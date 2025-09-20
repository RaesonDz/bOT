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
}

# رتب المستخدمين (بترتيب الأعلى إلى الأقل)
RANKS = {
    1: "VIP",
    2: "ماسي",
    3: "ذهبي",
    4: "فضي",
    5: "برونزي",
}

async def init_ranks():
    """تهيئة جدول الرتب في قاعدة البيانات"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            # إنشاء جدول الرتب إذا لم يكن موجودًا
            await db.execute('''
            CREATE TABLE IF NOT EXISTS ranks (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                min_balance REAL DEFAULT 0,
                features TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # إضافة عمود رتبة المستخدم إلى جدول المستخدمين إذا لم يكن موجودًا
            db.row_factory = sqlite3.Row
            cursor = await db.execute("PRAGMA table_info(users)")
            columns = await cursor.fetchall()
            column_names = [column["name"] for column in columns]

            if "rank_id" not in column_names:
                await db.execute("ALTER TABLE users ADD COLUMN rank_id INTEGER DEFAULT 5")
                # تحديث جميع المستخدمين الحاليين ليكونوا برونزيين (5) افتراضيًا
                await db.execute("UPDATE users SET rank_id = 5 WHERE rank_id IS NULL")

            # التحقق من وجود الرتب الأساسية وإنشائها إذا لم تكن موجودة
            for rank_id, rank_name in RANKS.items():
                cursor = await db.execute("SELECT id FROM ranks WHERE id = ?", (rank_id,))
                if not await cursor.fetchone():
                    features = ""
                    min_balance = 0

                    # إضافة ميزات حسب الرتبة
                    if rank_id == 1:  # VIP
                        features = "DISCOUNT,PRIORITY,SPECIAL_OFFER,ALL"
                        min_balance = 1000
                    elif rank_id == 2:  # ماسي
                        features = "DISCOUNT,PRIORITY,SPECIAL_OFFER"
                        min_balance = 500
                    elif rank_id == 3:  # ذهبي
                        features = "DISCOUNT,PRIORITY"
                        min_balance = 250
                    elif rank_id == 4:  # فضي
                        features = "DISCOUNT"
                        min_balance = 100

                    await db.execute(
                        "INSERT INTO ranks (id, name, min_balance, features) VALUES (?, ?, ?, ?)",
                        (rank_id, rank_name, min_balance, features)
                    )

            await db.commit()
            logger.info("تم تهيئة نظام الرتب بنجاح")
    except Exception as e:
        logger.error(f"خطأ في تهيئة نظام الرتب: {e}")

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
    return RANK_EMOJIS.get(rank_id, "🥉")  # استخدام رمز برونزي كافتراضي

def get_rank_name(rank_id: int) -> str:
    """الحصول على اسم الرتبة"""
    return RANKS.get(rank_id, "برونزي")  # استخدام برونزي كافتراضي

async def get_user_rank(user_id: int) -> Dict[str, Any]:
    """الحصول على رتبة المستخدم"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row

            # الحصول على معرف رتبة المستخدم
            cursor = await db.execute("SELECT rank_id FROM users WHERE user_id = ?", (user_id,))
            result = await cursor.fetchone()

            if not result:
                # المستخدم غير موجود، استخدام الرتبة الافتراضية (برونزي)
                return {"id": 5, "name": "برونزي", "features": []}

            rank_id = result["rank_id"] or 5  # استخدام 5 (برونزي) إذا كانت القيمة NULL

            # الحصول على معلومات الرتبة
            cursor = await db.execute("SELECT * FROM ranks WHERE id = ?", (rank_id,))
            rank = await cursor.fetchone()

            if not rank:
                # الرتبة غير موجودة، استخدام الرتبة الافتراضية (برونزي)
                return {"id": 5, "name": "برونزي", "features": []}

            # تحويل الرتبة إلى قاموس
            rank_dict = dict(rank)

            # تحويل سلسلة الميزات إلى قائمة
            features_str = rank_dict.get("features", "")
            features = features_str.split(",") if features_str else []
            rank_dict["features"] = features

            return rank_dict
    except Exception as e:
        logger.error(f"خطأ في الحصول على رتبة المستخدم: {e}")
        return {"id": 5, "name": "برونزي", "features": []}

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
    """تحديث رتب المستخدمين حسب الرصيد"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row

            # الحصول على جميع الرتب مرتبة تنازليًا حسب الحد الأدنى للرصيد
            cursor = await db.execute("SELECT id, min_balance FROM ranks ORDER BY min_balance DESC")
            ranks = await cursor.fetchall()

            # الحصول على جميع المستخدمين
            cursor = await db.execute("SELECT user_id, balance FROM users")
            users = await cursor.fetchall()

            # تحديث رتبة كل مستخدم
            for user in users:
                user_id = user["user_id"]
                balance = user["balance"]

                # تحديد الرتبة المناسبة
                new_rank_id = 5  # الرتبة الافتراضية (برونزي)
                for rank in ranks:
                    if balance >= rank["min_balance"]:
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
            db.row_factory = dict_factory
            cursor = await db.execute("SELECT * FROM ranks WHERE id = ?", (rank_id,))
            result = await cursor.fetchone()
            if result:
                return result
            else:
                return {"id": 5, "name": "برونزي", "emoji": "🥉"}
    except Exception as e:
        import logging
        logger = logging.getLogger("smm_bot")
        logger.error(f"Error getting rank by ID: {e}")
        return {"id": 5, "name": "برونزي", "emoji": "🥉"}


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