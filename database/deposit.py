"""
وحدة إدارة طلبات الإيداع
"""

import logging
import sqlite3
import aiosqlite
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import config
from database.core import update_user_balance, get_user

# إعداد المسجل
logger = logging.getLogger("smm_bot")

async def init_deposit_tables() -> None:
    """تهيئة جداول الإيداع"""
    async with aiosqlite.connect(config.DB_NAME) as db:
        # جدول الإيداعات
        await db.execute('''
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            payment_method TEXT,
            receipt_url TEXT,
            receipt_info TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            admin_id INTEGER,
            admin_note TEXT,
            transaction_id TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')

        # التحقق من وجود عمود admin_id وإضافته إذا لم يكن موجودًا
        cursor = await db.execute("PRAGMA table_info(deposits)")
        columns = await cursor.fetchall()
        column_names = [column[1] for column in columns]

        # إضافة الأعمدة إذا لم تكن موجودة
        if "admin_id" not in column_names:
            await db.execute("ALTER TABLE deposits ADD COLUMN admin_id INTEGER")

        if "admin_note" not in column_names:
            await db.execute("ALTER TABLE deposits ADD COLUMN admin_note TEXT")

        if "transaction_id" not in column_names:
            await db.execute("ALTER TABLE deposits ADD COLUMN transaction_id TEXT")

        if "receipt_info" not in column_names:
            await db.execute("ALTER TABLE deposits ADD COLUMN receipt_info TEXT")

        await db.commit()
        logger.info("تم تهيئة جداول الإيداع بنجاح")

async def create_deposit_request(user_id: int, amount: float, payment_method: str, receipt_url: str = None, receipt_info: str = None) -> int:
    """
    إنشاء طلب إيداع جديد

    Args:
        user_id: معرف المستخدم
        amount: المبلغ
        payment_method: طريقة الدفع
        receipt_url: عنوان URL لإيصال الدفع (اختياري)
        receipt_info: معلومات إضافية عن الإيصال (اختياري)

    Returns:
        معرف طلب الإيداع الجديد
    """
    try:
        # التحقق من أن المبلغ إيجابي
        if amount <= 0:
            logger.warning(f"محاولة إنشاء طلب إيداع بمبلغ غير صالح: {amount}")
            return -1

        async with aiosqlite.connect(config.DB_NAME) as db:
            cursor = await db.execute('''
            INSERT INTO deposits (user_id, amount, payment_method, receipt_url, receipt_info, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (user_id, amount, payment_method, receipt_url, receipt_info))
            await db.commit()

            deposit_id = cursor.lastrowid
            logger.info(f"تم إنشاء طلب إيداع جديد: {deposit_id} للمستخدم {user_id} بمبلغ {amount}")
            return deposit_id
    except Exception as e:
        logger.error(f"خطأ في إنشاء طلب إيداع: {e}")
        return -1

async def get_deposit_by_id(deposit_id: int) -> Optional[Dict[str, Any]]:
    """
    الحصول على معلومات طلب إيداع محدد بواسطة المعرف

    Args:
        deposit_id: معرف طلب الإيداع

    Returns:
        قاموس يحتوي على معلومات طلب الإيداع أو None إذا لم يتم العثور عليه
    """
    async with aiosqlite.connect(config.DB_NAME) as db:
        db.row_factory = sqlite3.Row # Corrected: Using sqlite3.Row for proper dictionary conversion

        query = """
            SELECT d.*, u.username, u.full_name
            FROM deposits d
            JOIN users u ON d.user_id = u.user_id
            WHERE d.id = ?
        """

        cursor = await db.execute(query, (deposit_id,))
        deposit = await cursor.fetchone()

        return dict(deposit) if deposit else None # Corrected: Handle None case

async def get_user_deposits(user_id: int) -> Tuple[List[Dict[str, Any]], int]:
    """
    الحصول على جميع طلبات الإيداع للمستخدم

    Args:
        user_id: معرف المستخدم

    Returns:
        قائمة بطلبات الإيداع والعدد الإجمالي
    """
    async with aiosqlite.connect(config.DB_NAME) as db:
        db.row_factory = sqlite3.Row

        # الحصول على العدد الإجمالي
        count_query = "SELECT COUNT(*) as count FROM deposits WHERE user_id = ?"
        cursor = await db.execute(count_query, (user_id,))
        count_result = await cursor.fetchone()
        total = count_result["count"] if count_result else 0

        # الحصول على طلبات الإيداع
        query = """
            SELECT d.*
            FROM deposits d
            WHERE d.user_id = ?
            ORDER BY d.created_at DESC
        """

        cursor = await db.execute(query, (user_id,))
        deposits = await cursor.fetchall()

        return [dict(deposit) for deposit in deposits], total

async def get_pending_deposits() -> Tuple[List[Dict[str, Any]], int]:
    """
    الحصول على طلبات الإيداع المعلقة

    Returns:
        (قائمة طلبات الإيداع المعلقة، العدد الإجمالي)
    """
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row

            # الحصول على طلبات الإيداع المعلقة
            cursor = await db.execute('''
            SELECT d.*, u.username, u.full_name
            FROM deposits d
            LEFT JOIN users u ON d.user_id = u.user_id
            WHERE d.status = 'pending'
            ORDER BY d.created_at DESC
            ''')

            deposits = await cursor.fetchall()

            # الحصول على العدد الإجمالي
            cursor = await db.execute("SELECT COUNT(*) as count FROM deposits WHERE status = 'pending'")
            result = await cursor.fetchone()
            total = result["count"] if result else 0

            return [dict(deposit) for deposit in deposits], total
    except Exception as e:
        logger.error(f"خطأ في الحصول على طلبات الإيداع المعلقة: {e}")
        return [], 0

async def get_all_deposits() -> Tuple[List[Dict[str, Any]], int]:
    """
    الحصول على جميع طلبات الإيداع

    Returns:
        (قائمة جميع طلبات الإيداع، العدد الإجمالي)
    """
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row

            # الحصول على جميع طلبات الإيداع
            cursor = await db.execute('''
            SELECT d.*, u.username, u.full_name
            FROM deposits d
            LEFT JOIN users u ON d.user_id = u.user_id
            ORDER BY d.created_at DESC
            ''')

            deposits = await cursor.fetchall()

            # الحصول على العدد الإجمالي
            cursor = await db.execute("SELECT COUNT(*) as count FROM deposits")
            result = await cursor.fetchone()
            total = result["count"] if result else 0

            return [dict(deposit) for deposit in deposits], total
    except Exception as e:
        logger.error(f"خطأ في الحصول على جميع طلبات الإيداع: {e}")
        return [], 0

async def approve_deposit(deposit_id: int, admin_id: int = None, admin_note: str = None, transaction_id: str = None) -> bool:
    """
    الموافقة على طلب إيداع

    Args:
        deposit_id: معرف طلب الإيداع
        admin_id: معرف المشرف الذي وافق على الطلب (اختياري)
        admin_note: ملاحظة المشرف (اختياري)
        transaction_id: معرف المعاملة (اختياري)

    Returns:
        True إذا نجحت العملية، False إذا فشلت
    """
    try:
        # الحصول على بيانات طلب الإيداع
        deposit = await get_deposit_by_id(deposit_id)

        if not deposit:
            logger.warning(f"محاولة الموافقة على طلب إيداع غير موجود: {deposit_id}")
            return False

        # التحقق من أن الطلب معلق
        if deposit["status"] != "pending":
            logger.warning(f"محاولة الموافقة على طلب إيداع غير معلق: {deposit_id}, الحالة: {deposit['status']}")
            return False

        user_id = deposit["user_id"]
        amount = deposit["amount"]
        payment_method = deposit["payment_method"]
        
        # حساب المبلغ بالدولار إذا كانت طريقة الدفع بالدينار الجزائري
        if payment_method == "BARIDIMOB":
            # تحويل المبلغ بالدينار إلى دولار (1$ = 260 دينار)
            amount_usd = amount / 260.0
        else:
            # طرق الدفع الأخرى تستخدم الدولار مباشرة
            amount_usd = amount

        # إضافة المبلغ بالدولار إلى رصيد المستخدم
        balance_updated = await update_user_balance(user_id, amount_usd, "add")

        if not balance_updated:
            logger.error(f"فشل في تحديث رصيد المستخدم {user_id} لطلب الإيداع {deposit_id}")
            return False

        # تحديث حالة طلب الإيداع
        async with aiosqlite.connect(config.DB_NAME) as db:
            await db.execute('''
            UPDATE deposits
            SET status = 'approved', updated_at = CURRENT_TIMESTAMP, admin_id = ?, admin_note = ?, transaction_id = ?
            WHERE id = ?
            ''', (admin_id, admin_note, transaction_id, deposit_id))
            await db.commit()

        logger.info(f"تمت الموافقة على طلب الإيداع {deposit_id} للمستخدم {user_id} بمبلغ {amount}")
        return True
    except Exception as e:
        logger.error(f"خطأ في الموافقة على طلب الإيداع: {e}")
        return False

async def update_deposit_transaction_id(deposit_id: int, transaction_id: str) -> bool:
    """
    تحديث رقم المعاملة لطلب الإيداع

    Args:
        deposit_id: معرف طلب الإيداع
        transaction_id: رقم المعاملة الجديد

    Returns:
        True إذا نجحت العملية، False إذا فشلت
    """
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            await db.execute('''
            UPDATE deposits
            SET transaction_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (transaction_id, deposit_id))
            await db.commit()

        logger.info(f"تم تحديث رقم المعاملة لطلب الإيداع {deposit_id}")
        return True
    except Exception as e:
        logger.error(f"خطأ في تحديث رقم المعاملة لطلب الإيداع: {e}")
        return False

async def reject_deposit(deposit_id: int, admin_id: int = None, admin_note: str = None) -> bool:
    """
    رفض طلب إيداع

    Args:
        deposit_id: معرف طلب الإيداع
        admin_id: معرف المشرف الذي رفض الطلب (اختياري)
        admin_note: ملاحظة المشرف (اختياري)

    Returns:
        True إذا نجحت العملية، False إذا فشلت
    """
    try:
        # الحصول على بيانات طلب الإيداع
        deposit = await get_deposit_by_id(deposit_id)

        if not deposit:
            logger.warning(f"محاولة رفض طلب إيداع غير موجود: {deposit_id}")
            return False

        # التحقق من أن الطلب معلق
        if deposit["status"] != "pending":
            logger.warning(f"محاولة رفض طلب إيداع غير معلق: {deposit_id}, الحالة: {deposit['status']}")
            return False

        # تحديث حالة طلب الإيداع
        async with aiosqlite.connect(config.DB_NAME) as db:
            await db.execute('''
            UPDATE deposits
            SET status = 'rejected', updated_at = CURRENT_TIMESTAMP, admin_id = ?, admin_note = ?
            WHERE id = ?
            ''', (admin_id, admin_note, deposit_id))
            await db.commit()

        logger.info(f"تم رفض طلب الإيداع {deposit_id}")
        return True
    except Exception as e:
        logger.error(f"خطأ في رفض طلب الإيداع: {e}")
        return False

async def refund_deposit(deposit_id: int, admin_id: int = None, admin_note: str = None) -> bool:
    """
    استرداد طلب إيداع تمت الموافقة عليه سابقاً
    
    Args:
        deposit_id: معرف طلب الإيداع
        admin_id: معرف المشرف الذي أمر بالاسترداد (اختياري)
        admin_note: ملاحظة المشرف (اختياري)
        
    Returns:
        True إذا نجحت العملية، False إذا فشلت
    """
    try:
        # الحصول على بيانات طلب الإيداع
        deposit = await get_deposit_by_id(deposit_id)
        
        if not deposit:
            logger.warning(f"محاولة استرداد طلب إيداع غير موجود: {deposit_id}")
            return False
            
        # التحقق من أن الطلب تمت الموافقة عليه 
        if deposit["status"] != "approved":
            logger.warning(f"محاولة استرداد طلب إيداع لم تتم الموافقة عليه: {deposit_id}, الحالة: {deposit['status']}")
            return False
            
        user_id = deposit["user_id"]
        amount = deposit["amount"]
        
        # خصم المبلغ من رصيد المستخدم
        from database.core import update_user_balance
        payment_method = deposit["payment_method"]
        
        # حساب المبلغ بالدولار إذا كانت طريقة الدفع بالدينار الجزائري
        if payment_method == "BARIDIMOB":
            # تحويل المبلغ بالدينار إلى دولار (1$ = 260 دينار)
            amount_usd = amount / 260.0
        else:
            # طرق الدفع الأخرى تستخدم الدولار مباشرة
            amount_usd = amount
            
        balance_updated = await update_user_balance(user_id, amount_usd, "subtract")
        
        if not balance_updated:
            logger.error(f"فشل في تحديث رصيد المستخدم {user_id} لاسترداد طلب الإيداع {deposit_id}")
            return False
            
        # تحديث حالة طلب الإيداع إلى "مسترد"
        async with aiosqlite.connect(config.DB_NAME) as db:
            await db.execute('''
            UPDATE deposits
            SET status = 'refunded', updated_at = CURRENT_TIMESTAMP, admin_id = ?, 
                admin_note = CASE WHEN ? IS NULL THEN admin_note ELSE ? END
            WHERE id = ?
            ''', (admin_id, admin_note, admin_note, deposit_id))
            await db.commit()
            
        logger.info(f"تم استرداد طلب الإيداع {deposit_id} للمستخدم {user_id} بمبلغ {amount}")
        return True
    except Exception as e:
        logger.error(f"خطأ في استرداد طلب الإيداع: {e}")
        return False

async def update_deposit_receipt(deposit_id: int, receipt_url: str = None, receipt_info: str = None) -> bool:
    """
    تحديث معلومات إيصال طلب الإيداع

    Args:
        deposit_id: معرف طلب الإيداع
        receipt_url: عنوان URL للإيصال (اختياري)
        receipt_info: معلومات إضافية للإيصال (اختياري)

    Returns:
        True إذا نجحت العملية، False إذا فشلت
    """
    try:
        # الحصول على بيانات طلب الإيداع
        deposit = await get_deposit_by_id(deposit_id)

        if not deposit:
            logger.warning(f"محاولة تحديث إيصال لطلب إيداع غير موجود: {deposit_id}")
            return False

        # التحقق من أن الطلب معلق
        if deposit["status"] != "pending":
            logger.warning(f"محاولة تحديث إيصال لطلب إيداع غير معلق: {deposit_id}, الحالة: {deposit['status']}")
            return False

        # تحديث معلومات الإيصال
        updates = []
        params = []

        if receipt_url is not None:
            updates.append("receipt_url = ?")
            params.append(receipt_url)

        if receipt_info is not None:
            updates.append("receipt_info = ?")
            params.append(receipt_info)

        if not updates:
            # لا توجد تحديثات للقيام بها
            return True

        # إضافة معرف طلب الإيداع ووقت التحديث
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(deposit_id)

        # تحديث طلب الإيداع
        async with aiosqlite.connect(config.DB_NAME) as db:
            await db.execute(
                f"UPDATE deposits SET {', '.join(updates)} WHERE id = ?",
                params
            )
            await db.commit()

        logger.info(f"تم تحديث معلومات إيصال طلب الإيداع {deposit_id}")
        return True
    except Exception as e:
        logger.error(f"خطأ في تحديث معلومات إيصال طلب الإيداع: {e}")
        return False

async def get_deposit_stats() -> Dict[str, Dict[str, Any]]:
    """
    الحصول على إحصائيات طلبات الإيداع

    Returns:
        قاموس يحتوي على إحصائيات طلبات الإيداع
    """
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            # دالة مساعدة لتحويل نتائج الاستعلام إلى قاموس
            def dict_factory(cursor, row):
                d = {}
                for idx, col in enumerate(cursor.description):
                    d[col[0]] = row[idx]
                return d

            db.row_factory = dict_factory

            # إحصائيات الطلبات المعلقة
            cursor = await db.execute('''
            SELECT COUNT(*) as count, SUM(amount) as total
            FROM deposits
            WHERE status = 'pending'
            ''')
            pending = await cursor.fetchone()

            # إحصائيات الطلبات المقبولة
            cursor = await db.execute('''
            SELECT COUNT(*) as count, SUM(amount) as total
            FROM deposits
            WHERE status = 'approved'
            ''')
            approved = await cursor.fetchone()

            # إحصائيات الطلبات المرفوضة
            cursor = await db.execute('''
            SELECT COUNT(*) as count, SUM(amount) as total
            FROM deposits
            WHERE status = 'rejected'
            ''')
            rejected = await cursor.fetchone()

            # إحصائيات طلبات اليوم
            today = datetime.now().strftime("%Y-%m-%d")
            cursor = await db.execute('''
            SELECT COUNT(*) as count, SUM(amount) as total
            FROM deposits
            WHERE date(created_at) = ?
            ''', (today,))
            today_stats = await cursor.fetchone()

            # تجميع الإحصائيات
            stats = {
                "pending": {
                    "count": pending["count"] or 0,
                    "total": pending["total"] or 0
                },
                "approved": {
                    "count": approved["count"] or 0,
                    "total": approved["total"] or 0
                },
                "rejected": {
                    "count": rejected["count"] or 0,
                    "total": rejected["total"] or 0
                },
                "today": {
                    "count": today_stats["count"] or 0,
                    "total": today_stats["total"] or 0
                }
            }

            return stats
    except Exception as e:
        logger.error(f"خطأ في الحصول على إحصائيات طلبات الإيداع: {e}")
        return {
            "pending": {"count": 0, "total": 0},
            "approved": {"count": 0, "total": 0},
            "rejected": {"count": 0, "total": 0},
            "today": {"count": 0, "total": 0}
        }

async def get_deposit_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    الحصول على تاريخ الإيداعات للمستخدم

    Args:
        user_id: معرف المستخدم
        limit: عدد السجلات المراد إرجاعها

    Returns:
        قائمة بسجلات الإيداع
    """
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute('''
            SELECT *
            FROM deposits
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            ''', (user_id, limit))

            deposits = await cursor.fetchall()

            return [dict(deposit) for deposit in deposits]
    except Exception as e:
        logger.error(f"خطأ في الحصول على تاريخ الإيداعات للمستخدم: {e}")
        return []