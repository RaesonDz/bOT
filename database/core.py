"""
وحدة قاعدة البيانات الأساسية
"""

import logging
import os
import sqlite3
import aiosqlite
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

import config

# إعداد المسجل
logger = logging.getLogger("smm_bot")

# مسارات قاعدة البيانات
DB_PATH = config.DB_NAME

async def update_order_remains(order_id: str, remains: int) -> bool:
    """
    تحديث الكمية المتبقية للطلب في قاعدة البيانات

    Args:
        order_id: معرف الطلب
        remains: الكمية المتبقية

    Returns:
        bool: نجاح العملية
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE orders SET remains = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
                (remains, order_id)
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"خطأ في تحديث الكمية المتبقية للطلب {order_id}: {e}")
        return False

async def init_db() -> None:
    """
    تهيئة قاعدة البيانات وإنشاء الجداول إذا لم تكن موجودة
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # جدول المستخدمين
        await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP
        )
        ''')

        # استرجاع معلومات جدول المستخدمين للتحقق
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        column_names = [column[1] for column in columns]
        logger.info(f"أعمدة جدول المستخدمين: {column_names}")

        # جدول الطلبات
        await db.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            user_id INTEGER,
            service_id INTEGER,
            service_name TEXT,
            link TEXT,
            quantity INTEGER,
            amount REAL,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')

        # التحقق من وجود عمود updated_at و remains وإضافتهم إذا لم يكونوا موجودين
        try:
            cursor = await db.execute("PRAGMA table_info(orders)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]

            if "updated_at" not in column_names:
                logger.info("إضافة عمود updated_at إلى جدول الطلبات")
                await db.execute("ALTER TABLE orders ADD COLUMN updated_at TIMESTAMP")
                # تحديث القيم الموجودة مباشرة بعد إضافة العمود
                await db.execute("UPDATE orders SET updated_at = created_at WHERE updated_at IS NULL")
                await db.commit()
                
            if "remains" not in column_names:
                logger.info("إضافة عمود remains إلى جدول الطلبات")
                await db.execute("ALTER TABLE orders ADD COLUMN remains INTEGER")
                # تعيين القيمة الافتراضية للكمية المتبقية بنفس قيمة الكمية الأصلية
                await db.execute("UPDATE orders SET remains = quantity WHERE remains IS NULL")
                
                # تحديث الطلبات المكتملة ليكون الرقم المتبقي 0
                await db.execute("UPDATE orders SET remains = 0 WHERE status = 'completed' OR status = 'Completed'")
                await db.commit()
                
                # إضافة سجل تنفيذ
                logger.info("تم تحديث جميع الطلبات المكتملة بحيث تكون الكمية المتبقية 0")
        except Exception as e:
            logger.error(f"خطأ في التحقق من أو إضافة أعمدة إلى جدول الطلبات: {e}")

        # جدول طلبات الإيداع
        await db.execute('''
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            payment_method TEXT,
            receipt_url TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')

        # التأكد من أن التعديلات تمت
        await db.commit()

    logger.info("تم تهيئة قاعدة البيانات بنجاح")

# وظائف المستخدمين
async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """
    الحصول على بيانات المستخدم من قاعدة البيانات

    Args:
        user_id: معرف المستخدم

    Returns:
        بيانات المستخدم أو None إذا لم يكن موجودًا
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?", 
                (user_id,)
            )
            user = await cursor.fetchone()

            if user:
                return dict(user)

            return None
    except Exception as e:
        logger.error(f"خطأ في الحصول على بيانات المستخدم (ID: {user_id}): {e}")
        return None

async def create_user(user_id: int, username: str, full_name: str) -> bool:
    """
    إنشاء مستخدم جديد في قاعدة البيانات

    Args:
        user_id: معرف المستخدم
        username: اسم المستخدم
        full_name: الاسم الكامل

    Returns:
        True إذا نجحت العملية، False إذا فشلت
    """
    try:
        # التحقق أولاً مما إذا كان المستخدم موجودًا بالفعل
        existing_user = await get_user(user_id)
        if existing_user:
            logger.info(f"المستخدم موجود بالفعل: {user_id}")
            return True  # المستخدم موجود بالفعل

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, balance, last_activity) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (user_id, username, full_name, 0)
            )
            await db.commit()
            logger.info(f"تم إنشاء مستخدم جديد: {user_id}, {username}")
            return True
    except sqlite3.IntegrityError:
        # في حالة محاولة إدخال مستخدم موجود (مفتاح رئيسي مكرر)
        logger.warning(f"محاولة إنشاء مستخدم موجود بالفعل: {user_id}")
        return True  # نعتبر ذلك نجاحًا لأن المستخدم موجود بالفعل
    except Exception as e:
        logger.error(f"خطأ في إنشاء المستخدم: {e}")
        return False

async def update_user_activity(user_id: int, timestamp: str) -> None:
    """
    تحديث وقت آخر نشاط للمستخدم

    Args:
        user_id: معرف المستخدم
        timestamp: الطابع الزمني
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_activity = ? WHERE user_id = ?",
            (timestamp, user_id)
        )
        await db.commit()

async def update_user_balance(user_id: int, amount: float, operation: str = "add") -> bool:
    """
    تحديث رصيد المستخدم

    Args:
        user_id: معرف المستخدم
        amount: المبلغ
        operation: نوع العملية (add للإضافة، subtract للخصم)

    Returns:
        True إذا نجحت العملية، False إذا فشلت
    """
    async with aiosqlite.connect(DB_PATH) as db:
        user = await get_user(user_id)

        if not user:
            return False

        current_balance = user["balance"]

        # حساب الرصيد الجديد
        if operation == "add":
            new_balance = current_balance + amount
        elif operation == "subtract":
            # التأكد من وجود رصيد كافٍ
            if current_balance < amount:
                return False
            new_balance = current_balance - amount
        else:
            return False

        # تحديث الرصيد
        await db.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (new_balance, user_id)
        )
        await db.commit()

        return True

async def get_all_users(page: int = 1, per_page: int = 10) -> Tuple[List[Dict[str, Any]], int]:
    """الحصول على جميع المستخدمين مع الصفحات"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = sqlite3.Row

            # حساب إجمالي المستخدمين
            cursor = await db.execute("SELECT COUNT(*) as count FROM users")
            result = await cursor.fetchone()
            total = result["count"]

            # حساب الإزاحة
            offset = (page - 1) * per_page

            # استرجاع المستخدمين
            cursor = await db.execute(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (per_page, offset)
            )

            users = await cursor.fetchall()

            return [dict(user) for user in users], total
    except Exception as e:
        logger.error(f"خطأ في الحصول على المستخدمين: {e}")
        return [], 0

async def get_orders_stats() -> Dict[str, Any]:
    """الحصول على إحصائيات الطلبات"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # تعريف dict_factory داخل الدالة لمنع خطأ الاسم غير معرف
            def dict_factory(cursor, row):
                """تحويل نتائج قاعدة البيانات إلى قاموس"""
                d = {}
                for idx, col in enumerate(cursor.description):
                    d[col[0]] = row[idx]
                return d

            db.row_factory = dict_factory

            # إجمالي عدد الطلبات
            cursor = await db.execute("SELECT COUNT(*) as count FROM orders")
            result = await cursor.fetchone()
            total_count = result["count"]

            # إجمالي مبلغ الطلبات
            cursor = await db.execute("SELECT SUM(amount) as total FROM orders") # Corrected column name to 'amount'
            result = await cursor.fetchone()
            total_amount = result["total"] or 0

            # إحصائيات حسب الفترة

            # اليوم
            today = datetime.now().strftime("%Y-%m-%d")
            cursor = await db.execute(
                "SELECT SUM(amount) as total FROM orders WHERE date(created_at) = ?", # Corrected column name to 'amount'
                (today,)
            )
            result = await cursor.fetchone()
            today_amount = result["total"] or 0

            # هذا الأسبوع
            # الحصول على تاريخ بداية الأسبوع (الأحد)
            now = datetime.now()
            start_of_week = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
            cursor = await db.execute(
                "SELECT SUM(amount) as total FROM orders WHERE date(created_at) >= ?", # Corrected column name to 'amount'
                (start_of_week,)
            )
            result = await cursor.fetchone()
            week_amount = result["total"] or 0

            # هذا الشهر
            start_of_month = now.strftime("%Y-%m-01")
            cursor = await db.execute(
                "SELECT SUM(amount) as total FROM orders WHERE date(created_at) >= ?", # Corrected column name to 'amount'
                (start_of_month,)
            )
            result = await cursor.fetchone()
            month_amount = result["total"] or 0

            # هذا العام
            start_of_year = now.strftime("%Y-01-01")
            cursor = await db.execute(
                "SELECT SUM(amount) as total FROM orders WHERE date(created_at) >= ?", # Corrected column name to 'amount'
                (start_of_year,)
            )
            result = await cursor.fetchone()
            year_amount = result["total"] or 0

            return {
                "total_count": total_count,
                "total_amount": total_amount,
                "today": today_amount,
                "this_week": week_amount,
                "this_month": month_amount,
                "this_year": year_amount
            }
    except Exception as e:
        logger.error(f"خطأ في الحصول على إحصائيات الطلبات: {e}")
        return {
            "total_count": 0,
            "total_amount": 0,
            "today": 0,
            "this_week": 0,
            "this_month": 0,
            "this_year": 0
        }

# وظائف الطلبات
async def create_order(user_id: int, order_id: str, service_id: int, service_name: str, 
                      link: str, quantity: int, amount: float) -> bool:
    """
    إنشاء طلب جديد في قاعدة البيانات

    Args:
        user_id: معرف المستخدم
        order_id: معرف الطلب من API
        service_id: معرف الخدمة
        service_name: اسم الخدمة
        link: رابط الطلب
        quantity: الكمية
        amount: المبلغ الإجمالي

    Returns:
        True إذا نجحت العملية، False إذا فشلت
    """
    # خصم المبلغ من رصيد المستخدم
    balance_updated = await update_user_balance(user_id, amount, "subtract")

    if not balance_updated:
        return False

    try:
        # إنشاء الطلب
        async with aiosqlite.connect(DB_PATH) as db:
            # التحقق من وجود عمود updated_at
            cursor = await db.execute("PRAGMA table_info(orders)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]

            # التحقق من وجود أعمدة updated_at و remains
            has_updated_at = "updated_at" in column_names
            has_remains = "remains" in column_names
            
            if has_updated_at and has_remains:
                # إذا كانت الأعمدة موجودة
                await db.execute(
                    """
                    INSERT INTO orders 
                    (order_id, user_id, service_id, service_name, link, quantity, amount, remains, updated_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (order_id, user_id, service_id, service_name, link, quantity, amount, quantity)
                )
            elif has_updated_at:
                # إذا كان عمود updated_at موجودًا فقط
                await db.execute(
                    """
                    INSERT INTO orders 
                    (order_id, user_id, service_id, service_name, link, quantity, amount, updated_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (order_id, user_id, service_id, service_name, link, quantity, amount)
                )
            elif has_remains:
                # إذا كان عمود remains موجودًا فقط
                await db.execute(
                    """
                    INSERT INTO orders 
                    (order_id, user_id, service_id, service_name, link, quantity, amount, remains) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (order_id, user_id, service_id, service_name, link, quantity, amount, quantity)
                )
            else:
                # إذا لم تكن الأعمدة موجودة
                await db.execute(
                    """
                    INSERT INTO orders 
                    (order_id, user_id, service_id, service_name, link, quantity, amount) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (order_id, user_id, service_id, service_name, link, quantity, amount)
                )

            await db.commit()
            return True
    except Exception as e:
        logger.error(f"خطأ في إنشاء الطلب: {e}")
        return False

async def get_user_orders(user_id: int, page: int = 1, per_page: int = 5) -> Tuple[List[Dict[str, Any]], int]:
    """
    الحصول على طلبات المستخدم مع الصفحات

    Args:
        user_id: معرف المستخدم
        page: رقم الصفحة
        per_page: عدد العناصر في الصفحة

    Returns:
        (قائمة الطلبات، إجمالي عدد الطلبات)
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = sqlite3.Row

            # التحقق مما إذا كان عمود remains موجودًا
            cursor = await db.execute("PRAGMA table_info(orders)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]
            has_remains = "remains" in column_names

            # استعلام للحصول على الطلبات مع معلومات الخدمة
            # استخدام IFNULL للتعامل مع حالة عدم وجود عمود updated_at
            if has_remains:
                query = """
                    SELECT 
                        o.id as id,
                        o.order_id,
                        o.service_id,
                        o.service_name,
                        o.link,
                        o.quantity,
                        o.amount,
                        o.status,
                        o.remains,
                        o.created_at,
                        IFNULL(o.updated_at, o.created_at) as updated_at
                    FROM orders o
                    WHERE o.user_id = ?
                    ORDER BY o.created_at DESC
                """
            else:
                query = """
                    SELECT 
                        o.id as id,
                        o.order_id,
                        o.service_id,
                        o.service_name,
                        o.link,
                        o.quantity,
                        o.amount,
                        o.status,
                        o.quantity as remains,
                        o.created_at,
                        IFNULL(o.updated_at, o.created_at) as updated_at
                    FROM orders o
                    WHERE o.user_id = ?
                    ORDER BY o.created_at DESC
                """

            # استعلام للحصول على العدد الإجمالي
            count_query = "SELECT COUNT(*) as total FROM orders WHERE user_id = ?"

            # تنفيذ الاستعلامات
            cursor = await db.execute(query, (user_id,))
            orders = await cursor.fetchall()

            cursor = await db.execute(count_query, (user_id,))
            count = await cursor.fetchone()
            total = dict(count)["total"] if count else 0

            # تحويل النتائج إلى قائمة من القواميس
            orders_list = []
            for order in orders:
                order_dict = dict(order)
                # التأكد من وجود جميع الحقول المطلوبة
                if not order_dict.get("order_id"):
                    order_dict["order_id"] = f"LOCAL-{order_dict.get('id', '0')}"

                if not order_dict.get("service_name"):
                    order_dict["service_name"] = "غير محدد"

                # تنسيق التاريخ بشكل أفضل إذا أمكن
                if order_dict.get("created_at"):
                    try:
                        created_at = datetime.fromisoformat(order_dict["created_at"].replace('Z', '+00:00'))
                        order_dict["created_at"] = created_at.strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        pass  # الاحتفاظ بالتنسيق الأصلي إذا فشل التحويل

                orders_list.append(order_dict)

            return orders_list, total
    except Exception as e:
        logger.error(f"خطأ في استرجاع طلبات المستخدم: {e}")
        return [], 0

async def handle_order_completion(user_id: int, order_id: str) -> None:
    """دالة مركزية للتعامل مع اكتمال الطلبات وفحص ترقية الرتب"""
    try:
        from database.ranks import increment_user_purchases_and_check_rank
        rank_result = await increment_user_purchases_and_check_rank(user_id)
        
        if rank_result.get("upgraded"):
            old_rank = rank_result.get("old_rank", {})
            new_rank = rank_result.get("new_rank", {})
            purchases = rank_result.get("purchases", 0)
            
            logger.info(f"🎉 تمت ترقية المستخدم {user_id} من {old_rank.get('name', 'غير محدد')} "
                       f"إلى {new_rank.get('name', 'غير محدد')} بعد {purchases} مشتريات مكتملة!")
    except Exception as rank_error:
        logger.error(f"خطأ في فحص ترقية الرتبة للمستخدم {user_id} عند اكتمال الطلب {order_id}: {rank_error}")

async def update_order_status(order_id: str, status: str) -> bool:
    """
    تحديث حالة الطلب

    Args:
        order_id: معرف الطلب
        status: الحالة الجديدة

    Returns:
        True إذا نجحت العملية، False إذا فشلت
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # تنظيف وتوحيد قيمة الحالة
            status = status.lower().strip().replace(" ", "_")
            
            # الحصول على user_id والحالة الحالية قبل التحديث لاستخدامهما في فحص الترقية
            cursor = await db.execute("SELECT user_id, status FROM orders WHERE order_id = ?", (order_id,))
            order_row = await cursor.fetchone()
            user_id = order_row[0] if order_row else None
            current_status = order_row[1] if order_row else None
            
            # تحديث الحالة
            await db.execute(
                "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
                (status, order_id)
            )
            await db.commit()
            logger.info(f"تم تحديث حالة الطلب #{order_id} إلى: {status}")
            
            # فحص ترقية الرتبة فقط عند التحول لحالة مكتمل من حالة أخرى (لتجنب التكرار)
            if status == "completed" and current_status != "completed" and user_id:
                await handle_order_completion(user_id, order_id)
            
            return True
    except Exception as e:
        logger.error(f"خطأ في تحديث حالة الطلب #{order_id}: {e}")
        return False

async def get_all_orders(status: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
    """استرجاع جميع الطلبات، مع إمكانية التصفية حسب الحالة"""
    try:
        query = """
            SELECT o.*, u.username, u.full_name
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
        """

        # إضافة التصفية حسب الحالة إذا تم تحديدها
        params = []
        if status:
            query += " WHERE o.status = ?"
            params.append(status)

        # إضافة الترتيب التنازلي حسب التاريخ
        query += " ORDER BY o.created_at DESC"

        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = dict_factory
            cursor = await db.execute(query, params)
            orders = await cursor.fetchall()

            # الحصول على العدد الإجمالي
            count_query = "SELECT COUNT(*) as count FROM orders"
            if status:
                count_query += " WHERE status = ?"

            cursor = await db.execute(count_query, params)
            result = await cursor.fetchone()
            total_count = result["count"] if result else 0

        return orders, total_count
    except Exception as e:
        logger.error(f"خطأ في استرجاع جميع الطلبات: {e}")
        return [], 0

async def get_recent_orders(limit: int = 5) -> List[Dict[str, Any]]:
    """استرجاع آخر الطلبات بحد أقصى محدد"""
    try:
        query = """
            SELECT o.*, u.username, u.full_name
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
            ORDER BY o.created_at DESC
            LIMIT ?
        """

        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = dict_factory
            cursor = await db.execute(query, (limit,))
            orders = await cursor.fetchall()

        return orders
    except Exception as e:
        logger.error(f"خطأ في استرجاع آخر الطلبات: {e}")
        return []

async def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """
    الحصول على تفاصيل طلب محدد بواسطة المعرف

    Args:
        order_id: معرف الطلب

    Returns:
        بيانات الطلب أو None إذا لم يكن موجودًا
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = sqlite3.Row

            # التحقق مما إذا كان عمود remains موجودًا
            cursor = await db.execute("PRAGMA table_info(orders)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]
            has_remains = "remains" in column_names

            # البحث أولاً عن الطلب باستخدام order_id
            if has_remains:
                query = """
                    SELECT 
                        o.id as id,
                        o.order_id,
                        o.user_id,
                        u.username,
                        u.full_name,
                        o.service_id,
                        o.service_name,
                        o.link,
                        o.quantity,
                        o.amount,
                        o.status,
                        o.remains,
                        o.created_at,
                        IFNULL(o.updated_at, o.created_at) as updated_at
                    FROM orders o
                    LEFT JOIN users u ON o.user_id = u.user_id
                    WHERE o.order_id = ?
                """
            else:
                query = """
                    SELECT 
                        o.id as id,
                        o.order_id,
                        o.user_id,
                        u.username,
                        u.full_name,
                        o.service_id,
                        o.service_name,
                        o.link,
                        o.quantity,
                        o.amount,
                        o.status,
                        o.quantity as remains,
                        o.created_at,
                        IFNULL(o.updated_at, o.created_at) as updated_at
                    FROM orders o
                    LEFT JOIN users u ON o.user_id = u.user_id
                    WHERE o.order_id = ?
                """

            cursor = await db.execute(query, (order_id,))
            order = await cursor.fetchone()

            # إذا لم يتم العثور على الطلب، نحاول البحث باستخدام المعرف الداخلي
            if not order and order_id.startswith("LOCAL-"):
                order_id_num = order_id.replace("LOCAL-", "")
                if order_id_num.isdigit():
                    cursor = await db.execute(
                        query.replace("o.order_id = ?", "o.id = ?"), 
                        (int(order_id_num),)
                    )
                    order = await cursor.fetchone()

            if not order:
                return None

            order_dict = dict(order)

            # التأكد من وجود معرف الطلب
            if not order_dict.get("order_id"):
                order_dict["order_id"] = f"LOCAL-{order_dict.get('id', '0')}"

            # تنسيق التاريخ بشكل أفضل إذا أمكن
            if order_dict.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(order_dict["created_at"].replace('Z', '+00:00'))
                    order_dict["created_at"] = created_at.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    pass

            return order_dict
    except Exception as e:
        logger.error(f"خطأ في استرجاع تفاصيل الطلب: {e}")
        return None

async def update_order_remains_simple(order_id: str, remains: int) -> bool:
    """
    تحديث الكمية المتبقية للطلب (نسخة بسيطة)
    
    تقوم هذه الدالة بتحديث الكمية المتبقية للطلب، وإذا كانت الكمية صفر،
    تقوم بتحديث حالة الطلب إلى "مكتمل"
    
    Args:
        order_id: معرف الطلب
        remains: الكمية المتبقية
        
    Returns:
        bool: نجاح العملية
    """
    try:
        # التأكد من أن القيمة رقمية
        remains_value = max(0, int(remains))  # لا يمكن أن تكون القيمة سالبة
        order_id_str = str(order_id).strip()
        
        if not order_id_str:
            logger.error("معرف الطلب فارغ، تعذر تحديث الكمية المتبقية")
            return False
        
        async with aiosqlite.connect(DB_PATH) as db:
            # تحقق من وجود العمود
            cursor = await db.execute("PRAGMA table_info(orders)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            if "remains" not in column_names:
                # إضافة عمود remains إذا لم يكن موجودًا
                await db.execute("ALTER TABLE orders ADD COLUMN remains INTEGER DEFAULT NULL")
                await db.commit()
                logger.info("تمت إضافة عمود remains إلى جدول orders")
            
            # جلب حالة الطلب الحالية و user_id للاستخدام في فحص الترقية
            cursor = await db.execute(
                "SELECT status, user_id FROM orders WHERE order_id = ?",
                (order_id_str,)
            )
            order_row = await cursor.fetchone()
            current_status = order_row[0] if order_row else None
            user_id = order_row[1] if order_row else None
            
            logger.debug(f"حالة الطلب #{order_id_str} الحالية: {current_status}, الكمية المتبقية الجديدة: {remains_value}")
            
            # تحديث قيمة remains للطلب المحدد
            await db.execute(
                "UPDATE orders SET remains = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
                (remains_value, order_id_str)
            )
            
            # منطق تحديث الحالة:
            # - إذا كانت الكمية المتبقية 0 ولم تكن الحالة "completed" أو "partial" بالفعل، غيرها إلى "completed"
            # - ملاحظة: الحالة "partial" تشير إلى أن الطلب اكتمل جزئيًا ولا يمكن إكماله أكثر
            update_status = False
            new_status = None
            
            if remains_value == 0:
                if current_status not in ["completed", "partial"]:
                    new_status = "completed"
                    update_status = True
            else:
                # إذا كانت الكمية المتبقية أكبر من 0 والحالة "completed"، قم بتحديثها إلى "processing"
                if current_status == "completed":
                    new_status = "processing"
                    update_status = True
            
            # تنفيذ تحديث الحالة إذا لزم الأمر
            if update_status and new_status:
                await db.execute(
                    "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?",
                    (new_status, order_id_str)
                )
                logger.info(f"تم تحديث حالة الطلب #{order_id_str} من {current_status} إلى {new_status}")
                
                # سنقوم بفحص ترقية الرتبة بعد الcommit لضمان سلامة البيانات
                rank_upgrade_needed = (new_status == "completed" and user_id)
            
            await db.commit()
            logger.info(f"تم تحديث الكمية المتبقية للطلب #{order_id_str} إلى: {remains_value}")
            
            # فحص ترقية الرتبة التلقائية بعد commit لضمان سلامة البيانات
            if 'rank_upgrade_needed' in locals() and rank_upgrade_needed:
                await handle_order_completion(user_id, order_id_str)
            
            return True
    except Exception as e:
        logger.error(f"خطأ في تحديث الكمية المتبقية للطلب #{order_id}: {e}")
        return False

async def get_user_count():
    """الحصول على عدد المستخدمين"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) as count FROM users")
        result = await cursor.fetchone()
        return result[0] if result else 0

async def get_deposit_count():
    """الحصول على عدد عمليات الإيداع"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) as count FROM deposits")
        result = await cursor.fetchone()
        return result[0] if result else 0

async def get_order_count():
    """الحصول على عدد الطلبات"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) as count FROM orders")
        result = await cursor.fetchone()
        return result[0] if result else 0

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

async def get_all_users_simple(limit=None):
    """استرجاع جميع المستخدمين بشكل بسيط"""
    async with aiosqlite.connect(DB_PATH) as db:
        # تنفيذ الاستعلام
        if limit:
            query = "SELECT * FROM users ORDER BY created_at DESC LIMIT ?"
            cursor = await db.execute(query, (limit,))
        else:
            query = "SELECT * FROM users ORDER BY created_at DESC"
            cursor = await db.execute(query)

        # استرجاع النتائج
        rows = await cursor.fetchall()

        # تحويل النتائج إلى قائمة من القواميس
        users = []
        for row in rows:
            # بناء على بنية الجدول: user_id, username, full_name, balance, created_at, last_activity, rank_id
            user = {
                "user_id": row[0] if len(row) > 0 else 0,
                "username": row[1] if len(row) > 1 else "غير محدد",
                "full_name": row[2] if len(row) > 2 else "غير محدد",
                "balance": row[3] if len(row) > 3 else 0,
                "created_at": row[4] if len(row) > 4 else None,
                "last_activity": row[5] if len(row) > 5 else None,
                "rank_id": row[6] if len(row) > 6 else 5  # رتبة افتراضية
            }
                
            users.append(user)

        # استرجاع إجمالي عدد المستخدمين
        count_cursor = await db.execute("SELECT COUNT(*) FROM users")
        count_row = await count_cursor.fetchone()
        total_users = count_row[0]

        return users, total_users

async def get_active_users(days=30):
    """استرجاع المستخدمين النشطين خلال فترة محددة"""
    from datetime import datetime, timedelta

    # حساب تاريخ البداية للفترة المحددة
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')

    async with aiosqlite.connect(DB_PATH) as db:
        # تنفيذ الاستعلام
        query = "SELECT * FROM users WHERE last_activity > ? ORDER BY last_activity DESC"
        cursor = await db.execute(query, (start_date,))

        # استرجاع النتائج
        rows = await cursor.fetchall()

        # تحويل النتائج إلى قائمة من القواميس
        users = []
        for row in rows:
            # بناء على بنية الجدول: user_id, username, full_name, balance, created_at, last_activity, rank_id
            user = {
                "user_id": row[0],
                "username": row[1],
                "full_name": row[2],
                "balance": row[3],
                "created_at": row[4],
                "last_activity": row[5],
                "rank_id": row[6] if len(row) > 6 else 5  # رتبة افتراضية
            }
            users.append(user)

        # استرجاع إجمالي عدد المستخدمين النشطين
        count_cursor = await db.execute("SELECT COUNT(*) FROM users WHERE last_activity > ?", (start_date,))
        count_row = await count_cursor.fetchone()
        total_active_users = count_row[0]

        return users, total_active_users

async def get_system_stats():
    """استرجاع إحصائيات النظام العامة"""
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}

        # إجمالي عدد المستخدمين
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        stats["total_users"] = row[0]

        # المستخدمين النشطين في آخر 24 ساعة
        from datetime import datetime, timedelta
        last_24h = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE last_activity > ?", (last_24h,))
        row = await cursor.fetchone()
        stats["active_users_24h"] = row[0]

        # المستخدمين النشطين في آخر 7 أيام
        last_7d = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE last_activity > ?", (last_7d,))
        row = await cursor.fetchone()
        stats["active_users_7d"] = row[0]

        # المستخدمين الجدد في آخر 24 ساعة
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE created_at > ?", (last_24h,))
        row = await cursor.fetchone()
        stats["new_users_24h"] = row[0]

        # إجمالي رصيد المستخدمين
        cursor = await db.execute("SELECT SUM(balance) FROM users")
        row = await cursor.fetchone()
        stats["total_balance"] = row[0] or 0

        return stats
async def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """
    تنفيذ استعلام SQL في قاعدة البيانات
    
    Args:
        query: استعلام SQL للتنفيذ
        params: معلمات الاستعلام (اختياري)
        fetch_one: استرداد سجل واحد فقط
        fetch_all: استرداد جميع السجلات
        
    Returns:
        النتيجة حسب المعلمات
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = dict_factory
            
            if params:
                cursor = await db.execute(query, params)
            else:
                cursor = await db.execute(query)
                
            if fetch_one:
                result = await cursor.fetchone()
                return result
            elif fetch_all:
                result = await cursor.fetchall()
                return result
            else:
                await db.commit()
                return True
    except Exception as e:
        logger.error(f"خطأ في تنفيذ الاستعلام: {e}")
        return None if fetch_one or fetch_all else False
