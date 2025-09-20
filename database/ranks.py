"""
وحدة إدارة رتب المستخدمين
"""

import logging
import sqlite3
import aiosqlite
from typing import Dict, List, Optional, Any, Tuple

import config
from database.core import get_user

# إعداد المسجل
logger = logging.getLogger("smm_bot")

# رموز الرتب
RANK_EMOJIS = {
    1: "👑",  # VIP
    2: "💎",  # ماسي
    3: "🥇",  # ذهبي
    4: "🥈",  # فضي
    5: "🥉",  # برونزي
    6: "🆕",  # جديد
}

# رتب المستخدمين (بترتيب الأعلى إلى الأقل) - نظام معتمد على عدد المشتريات
RANKS = {
    1: "VIP",        # 200+ مشتريات، خصم 5%
    2: "ماسي",       # 100+ مشتريات، خصم 10%
    3: "ذهبي",       # 75+ مشتريات، خصم 15%
    4: "فضي",        # 50+ مشتريات، خصم 20%
    5: "برونزي",     # 25+ مشتريات، بدون خصم
    6: "جديد",       # 0+ مشتريات، بدون خصم
}

async def init_ranks():
    """تهيئة جدول الرتب في قاعدة البيانات (مُعطل - يتم استخدام المigrations بدلاً منه)"""
    # هذه الدالة معطلة لتجنب التضارب مع نظام المigrations الجديد
    # يتم تهيئة الرتب عبر migration v5 بدلاً من هذه الدالة
    logger.info("تم تخطي init_ranks - يتم استخدام نظام المigrations")

async def get_all_ranks() -> List[Dict[str, Any]]:
    """الحصول على قائمة جميع الرتب"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute("SELECT * FROM ranks ORDER BY id ASC")
            ranks = await cursor.fetchall()

            # تحويل الرتب إلى قائمة من القواميس
            result = []
            for rank in ranks:
                rank_dict = dict(rank)
                # تحويل سلسلة الميزات إلى قائمة
                features_str = rank_dict.get("features", "")
                features = features_str.split(",") if features_str else []
                rank_dict["features"] = features
                result.append(rank_dict)

            return result
    except Exception as e:
        logger.error(f"خطأ في الحصول على قائمة الرتب: {e}")
        return []

def get_rank_emoji(rank_id: int) -> str:
    """الحصول على رمز الرتبة"""
    return RANK_EMOJIS.get(rank_id, "🆕")  # استخدام رمز جديد كافتراضي

def get_rank_name(rank_id: int) -> str:
    """الحصول على اسم الرتبة"""
    return RANKS.get(rank_id, "جديد")  # استخدام جديد كافتراضي

async def get_user_rank(user_id: int) -> Dict[str, Any]:
    """الحصول على رتبة المستخدم"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row

            # الحصول على معرف رتبة المستخدم
            cursor = await db.execute("SELECT rank_id FROM users WHERE user_id = ?", (user_id,))
            result = await cursor.fetchone()

            if not result:
                # المستخدم غير موجود، استخدام الرتبة الافتراضية (جديد)
                return {"id": 6, "name": "جديد", "features": []}

            rank_id = result["rank_id"] or 6  # استخدام 6 (جديد) إذا كانت القيمة NULL

            # الحصول على معلومات الرتبة
            cursor = await db.execute("SELECT * FROM ranks WHERE id = ?", (rank_id,))
            rank = await cursor.fetchone()

            if not rank:
                # الرتبة غير موجودة، استخدام الرتبة الافتراضية (جديد)
                return {"id": 6, "name": "جديد", "features": []}

            # تحويل الرتبة إلى قاموس
            rank_dict = dict(rank)

            # تحويل سلسلة الميزات إلى قائمة
            features_str = rank_dict.get("features", "")
            features = features_str.split(",") if features_str else []
            rank_dict["features"] = features

            return rank_dict
    except Exception as e:
        logger.error(f"خطأ في الحصول على رتبة المستخدم: {e}")
        return {"id": 6, "name": "جديد", "features": []}

async def update_user_rank(user_id: int, rank_id: int) -> bool:
    """تحديث رتبة المستخدم"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            # التحقق من وجود المستخدم
            cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not await cursor.fetchone():
                logger.warning(f"محاولة تحديث رتبة لمستخدم غير موجود: {user_id}")
                return False

            # التحقق من وجود الرتبة
            cursor = await db.execute("SELECT id FROM ranks WHERE id = ?", (rank_id,))
            if not await cursor.fetchone():
                logger.warning(f"محاولة تعيين رتبة غير موجودة: {rank_id}")
                return False

            # تحديث رتبة المستخدم
            await db.execute("UPDATE users SET rank_id = ? WHERE user_id = ?", (rank_id, user_id))
            await db.commit()

            logger.info(f"تم تحديث رتبة المستخدم {user_id} إلى {rank_id}")
            return True
    except Exception as e:
        logger.error(f"خطأ في تحديث رتبة المستخدم: {e}")
        return False

async def update_users_ranks():
    """تحديث رتب المستخدمين حسب عدد المشتريات المكتملة"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row

            # الحصول على جميع الرتب مرتبة تنازلياً حسب عدد المشتريات
            cursor = await db.execute("SELECT id, min_purchases FROM ranks ORDER BY min_purchases DESC")
            ranks = await cursor.fetchall()

            # الحصول على جميع المستخدمين
            cursor = await db.execute("SELECT user_id, completed_purchases FROM users")
            users = await cursor.fetchall()

            # تحديث رتبة كل مستخدم
            for user in users:
                user_id = user["user_id"]
                purchases = user["completed_purchases"] or 0

                # تحديد الرتبة المناسبة
                new_rank_id = 6  # جديد (افتراضي)
                for rank in ranks:
                    if purchases >= rank["min_purchases"]:
                        new_rank_id = rank["id"]
                        break

                # تحديث الرتبة إذا كانت مختلفة
                await db.execute(
                    "UPDATE users SET rank_id = ? WHERE user_id = ? AND (rank_id IS NULL OR rank_id != ?)",
                    (new_rank_id, user_id, new_rank_id)
                )

            await db.commit()
            logger.info("تم تحديث رتب المستخدمين بنجاح")
            return True
    except Exception as e:
        logger.error(f"خطأ في تحديث رتب المستخدمين: {e}")
        return False

async def get_rank_by_id(rank_id: int) -> Dict[str, Any]:
    """Gets rank details by ID."""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute("SELECT * FROM ranks WHERE id = ?", (rank_id,))
            result = await cursor.fetchone()
            if result:
                return dict(result)
            else:
                return {"id": 6, "name": "جديد", "emoji": "🆕"}
    except Exception as e:
        logger.error(f"Error getting rank by ID: {e}")
        return {"id": 6, "name": "جديد", "emoji": "🆕"}

async def increment_user_purchases_and_check_rank(user_id: int) -> Dict[str, Any]:
    """زيادة عدد المشتريات المكتملة للمستخدم وفحص إمكانية الترقية التلقائية"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            # زيادة عدد المشتريات المكتملة
            await db.execute(
                "UPDATE users SET completed_purchases = COALESCE(completed_purchases, 0) + 1 WHERE user_id = ?",
                (user_id,)
            )
            
            # الحصول على عدد المشتريات الحالي
            cursor = await db.execute(
                "SELECT completed_purchases, rank_id FROM users WHERE user_id = ?",
                (user_id,)
            )
            user = await cursor.fetchone()
            
            if not user:
                logger.warning(f"لم يتم العثور على المستخدم {user_id}")
                return {"upgraded": False, "error": "المستخدم غير موجود"}
            
            purchases = user["completed_purchases"]
            current_rank_id = user["rank_id"]
            
            # تحديد الرتبة الجديدة المناسبة
            new_rank_id = 6  # جديد (افتراضي)
            if purchases >= 200:
                new_rank_id = 1  # VIP
            elif purchases >= 100:
                new_rank_id = 2  # ماسي
            elif purchases >= 75:
                new_rank_id = 3  # ذهبي
            elif purchases >= 50:
                new_rank_id = 4  # فضي
            elif purchases >= 25:
                new_rank_id = 5  # برونزي
            
            # فحص إذا كانت هناك ترقية
            upgraded = False
            old_rank = None
            new_rank = None
            
            if new_rank_id != current_rank_id:
                # تحديث الرتبة
                await db.execute(
                    "UPDATE users SET rank_id = ? WHERE user_id = ?",
                    (new_rank_id, user_id)
                )
                
                # الحصول على معلومات الرتب للإشعار
                cursor = await db.execute(
                    "SELECT name, emoji, discount_percentage FROM ranks WHERE id = ?",
                    (current_rank_id,)
                )
                old_rank_info = await cursor.fetchone()
                
                cursor = await db.execute(
                    "SELECT name, emoji, discount_percentage FROM ranks WHERE id = ?",
                    (new_rank_id,)
                )
                new_rank_info = await cursor.fetchone()
                
                upgraded = True
                old_rank = dict(old_rank_info) if old_rank_info else None
                new_rank = dict(new_rank_info) if new_rank_info else None
                
                logger.info(f"تمت ترقية المستخدم {user_id} من {current_rank_id} إلى {new_rank_id}")
            
            await db.commit()
            
            return {
                "upgraded": upgraded,
                "purchases": purchases,
                "old_rank": old_rank,
                "new_rank": new_rank,
                "current_rank_id": new_rank_id
            }
            
    except Exception as e:
        logger.error(f"خطأ في زيادة المشتريات وفحص الرتبة للمستخدم {user_id}: {e}")
        return {"upgraded": False, "error": str(e)}

async def get_user_rank_discount(user_id: int) -> float:
    """الحصول على نسبة الخصم للمستخدم حسب رتبته"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            cursor = await db.execute("""
                SELECT r.discount_percentage 
                FROM users u 
                JOIN ranks r ON u.rank_id = r.id 
                WHERE u.user_id = ?
            """, (user_id,))
            
            result = await cursor.fetchone()
            return result["discount_percentage"] if result else 0.0
            
    except Exception as e:
        logger.error(f"خطأ في الحصول على خصم المستخدم {user_id}: {e}")
        return 0.0

async def get_user_purchases_count(user_id: int) -> int:
    """الحصول على عدد المشتريات المكتملة للمستخدم"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            cursor = await db.execute(
                "SELECT completed_purchases FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = await cursor.fetchone()
            return result[0] if result and result[0] is not None else 0
            
    except Exception as e:
        logger.error(f"خطأ في الحصول على عدد مشتريات المستخدم {user_id}: {e}")
        return 0

async def get_user_discount_percentage(user_id: int) -> float:
    """الحصول على نسبة الخصم للمستخدم حسب رتبته (دالة مساعدة للتسعير)"""
    return await get_user_rank_discount(user_id)

async def get_user_completed_purchases(user_id: int) -> int:
    """الحصول على عدد المشتريات المكتملة للمستخدم (دالة مساعدة للتسعير)"""
    return await get_user_purchases_count(user_id)


async def create_ranks_table():
    """إنشاء جدول الرتب إذا لم يكن موجودًا"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            # إنشاء جدول الرتب
            await db.execute("""
            CREATE TABLE IF NOT EXISTS ranks (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                emoji TEXT NOT NULL,
                min_deposit REAL DEFAULT 0,
                discount REAL DEFAULT 0
            )
            """)

            # إضافة عمود rank_id إلى جدول المستخدمين إذا لم يكن موجودًا
            cursor = await db.execute("PRAGMA table_info(users)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]

            # التحقق مما إذا كان عمود rank_id موجودًا
            if 'rank_id' not in column_names:
                await db.execute("ALTER TABLE users ADD COLUMN rank_id INTEGER DEFAULT 5")

            # إدخال الرتب الافتراضية إذا لم تكن موجودة
            ranks_data = [
                (1, "ماسي", "💎", 1000, 0.20),
                (2, "ذهبي", "🥇", 500, 0.15),
                (3, "فضي", "🥈", 200, 0.10),
                (4, "برونزي+", "🥉+", 100, 0.05),
                (5, "برونزي", "🥉", 0, 0.00)
            ]

            for rank in ranks_data:
                cursor = await db.execute("SELECT id FROM ranks WHERE id = ?", (rank[0],))
                if not await cursor.fetchone():
                    await db.execute(
                        "INSERT INTO ranks (id, name, emoji, min_deposit, discount) VALUES (?, ?, ?, ?, ?)",
                        rank
                    )
            
            await db.commit()
            return True
    except Exception as e:
        import logging
        logger = logging.getLogger("smm_bot")
        logger.error(f"خطأ في إنشاء جدول الرتب: {e}")
        return False