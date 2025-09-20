"""
نظام migrations لقاعدة البيانات

يدير تطبيق التحديثات على قاعدة البيانات بشكل منظم ومتسلسل
"""

import logging
import sqlite3
import aiosqlite
from typing import Dict, List, Optional, Any
from datetime import datetime

import config

# إعداد المسجل
logger = logging.getLogger("smm_bot")

# إصدار schema الحالي
CURRENT_SCHEMA_VERSION = 4

async def init_migrations_table():
    """تهيئة جدول migrations لتتبع إصدارات قاعدة البيانات"""
    async with aiosqlite.connect(config.DB_NAME) as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
        ''')
        await db.commit()
        logger.info("تم تهيئة جدول migrations")

async def get_current_schema_version() -> int:
    """الحصول على إصدار schema الحالي"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            cursor = await db.execute(
                "SELECT MAX(version) as version FROM schema_migrations"
            )
            result = await cursor.fetchone()
            return result[0] if result[0] is not None else 0
    except Exception as e:
        logger.warning(f"لا يمكن الحصول على إصدار schema: {e}")
        return 0

async def apply_migration(version: int, description: str, migration_sql: str):
    """تطبيق migration معين"""
    async with aiosqlite.connect(config.DB_NAME) as db:
        try:
            # تطبيق SQL statements
            for statement in migration_sql.split(';'):
                statement = statement.strip()
                if statement:
                    await db.execute(statement)
            
            # تسجيل المigration كمطبق
            await db.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (version, description)
            )
            await db.commit()
            logger.info(f"تم تطبيق migration {version}: {description}")
        except Exception as e:
            await db.rollback()
            logger.error(f"فشل في تطبيق migration {version}: {e}")
            raise

async def migration_v1_services_and_categories():
    """Migration 1: إضافة جداول الخدمات والفئات"""
    async with aiosqlite.connect(config.DB_NAME) as db:
        try:
            # إنشاء جدول categories أولاً
            await db.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                display_order INTEGER DEFAULT 0,
                visibility_min_rank INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # إنشاء جدول services
            await db.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id INTEGER UNIQUE,
                category_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                base_price REAL NOT NULL DEFAULT 0,
                min_quantity INTEGER DEFAULT 1,
                max_quantity INTEGER DEFAULT 10000,
                is_active BOOLEAN DEFAULT 1,
                visibility_min_rank INTEGER DEFAULT 5,
                raw_api_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories (id)
            )
            ''')
            
            # إنشاء الفهارس
            await db.execute("CREATE INDEX IF NOT EXISTS idx_services_category ON services(category_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_services_active ON services(is_active)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_services_external_id ON services(external_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_categories_active ON categories(is_active)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_categories_visibility ON categories(visibility_min_rank)")
            
            # تسجيل المigration كمطبق
            await db.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (1, "إضافة جداول الخدمات والفئات")
            )
            await db.commit()
            logger.info("تم تطبيق migration 1: إضافة جداول الخدمات والفئات")
        except Exception as e:
            await db.rollback()
            logger.error(f"فشل في تطبيق migration 1: {e}")
            raise

async def migration_v2_pricing_rules():
    """Migration 2: إضافة نظام قواعد التسعير"""
    async with aiosqlite.connect(config.DB_NAME) as db:
        try:
            # إنشاء جدول pricing_rules
            await db.execute('''
            CREATE TABLE IF NOT EXISTS pricing_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                scope TEXT NOT NULL CHECK (scope IN ('global', 'category', 'service')),
                ref_id INTEGER,
                rank_id INTEGER,
                percentage REAL DEFAULT 0 CHECK (percentage >= -90 AND percentage <= 1000),
                fixed_fee REAL DEFAULT 0 CHECK (fixed_fee >= 0),
                is_active BOOLEAN DEFAULT 1,
                starts_at TIMESTAMP,
                ends_at TIMESTAMP,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (user_id),
                FOREIGN KEY (rank_id) REFERENCES ranks (id)
            )
            ''')
            
            # إنشاء الفهارس المحسنة
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pricing_rules_scope_ref ON pricing_rules(scope, ref_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pricing_rules_rank ON pricing_rules(rank_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pricing_rules_active ON pricing_rules(is_active)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pricing_rules_time ON pricing_rules(starts_at, ends_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pricing_rules_composite ON pricing_rules(scope, ref_id, rank_id, is_active)")
            
            # تسجيل المigration كمطبق
            await db.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (2, "إضافة نظام قواعد التسعير")
            )
            await db.commit()
            logger.info("تم تطبيق migration 2: إضافة نظام قواعد التسعير")
        except Exception as e:
            await db.rollback()
            logger.error(f"فشل في تطبيق migration 2: {e}")
            raise

async def migration_v3_crypto_system():
    """Migration 3: إضافة نظام العملات المشفرة"""
    async with aiosqlite.connect(config.DB_NAME) as db:
        try:
            # إنشاء جدول crypto_wallets
            await db.execute('''
            CREATE TABLE IF NOT EXISTS crypto_wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                asset TEXT NOT NULL,
                network TEXT NOT NULL,
                address TEXT NOT NULL UNIQUE,
                tag TEXT,
                sub_account_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(user_id, asset, network)
            )
            ''')
            
            # إنشاء جدول crypto_transactions
            await db.execute('''
            CREATE TABLE IF NOT EXISTS crypto_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('deposit', 'withdraw')),
                amount REAL NOT NULL,
                asset TEXT NOT NULL,
                network TEXT NOT NULL,
                address TEXT,
                txid TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                confirmations INTEGER DEFAULT 0,
                fee REAL DEFAULT 0,
                raw_data TEXT,
                admin_id INTEGER,
                admin_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (admin_id) REFERENCES users (user_id)
            )
            ''')
            
            # إنشاء الفهارس
            await db.execute("CREATE INDEX IF NOT EXISTS idx_crypto_wallets_user ON crypto_wallets(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_crypto_wallets_asset ON crypto_wallets(asset, network)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_crypto_wallets_active ON crypto_wallets(is_active)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_crypto_transactions_user ON crypto_transactions(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_crypto_transactions_txid ON crypto_transactions(txid)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_crypto_transactions_status ON crypto_transactions(status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_crypto_transactions_asset ON crypto_transactions(asset, network)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_crypto_transactions_address ON crypto_transactions(address)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_crypto_transactions_created ON crypto_transactions(created_at)")
            
            # تسجيل المigration كمطبق
            await db.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (3, "إضافة نظام العملات المشفرة")
            )
            await db.commit()
            logger.info("تم تطبيق migration 3: إضافة نظام العملات المشفرة")
        except Exception as e:
            await db.rollback()
            logger.error(f"فشل في تطبيق migration 3: {e}")
            raise

async def migration_v4_enhanced_deposits():
    """Migration 4: تحسين نظام الإيداعات"""
    migration_sql = '''
    ALTER TABLE deposits ADD COLUMN receipt_fields TEXT;
    ALTER TABLE deposits ADD COLUMN verifier_admin_id INTEGER;
    ALTER TABLE deposits ADD COLUMN verified_at TIMESTAMP;
    ALTER TABLE deposits ADD COLUMN review_notes TEXT;
    ALTER TABLE deposits ADD COLUMN auto_approved BOOLEAN DEFAULT 0;
    '''
    
    # تطبيق التعديلات بحذر (قد تكون الأعمدة موجودة)
    async with aiosqlite.connect(config.DB_NAME) as db:
        try:
            # فحص الأعمدة الموجودة
            cursor = await db.execute("PRAGMA table_info(deposits)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            # إضافة الأعمدة الجديدة إذا لم تكن موجودة
            if "receipt_fields" not in column_names:
                await db.execute("ALTER TABLE deposits ADD COLUMN receipt_fields TEXT")
            
            if "verifier_admin_id" not in column_names:
                await db.execute("ALTER TABLE deposits ADD COLUMN verifier_admin_id INTEGER")
            
            if "verified_at" not in column_names:
                await db.execute("ALTER TABLE deposits ADD COLUMN verified_at TIMESTAMP")
            
            if "review_notes" not in column_names:
                await db.execute("ALTER TABLE deposits ADD COLUMN review_notes TEXT")
                
            if "auto_approved" not in column_names:
                await db.execute("ALTER TABLE deposits ADD COLUMN auto_approved BOOLEAN DEFAULT 0")
            
            # تسجيل المigration كمطبق
            await db.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (4, "تحسين نظام الإيداعات")
            )
            await db.commit()
            logger.info("تم تطبيق migration 4: تحسين نظام الإيداعات")
        except Exception as e:
            await db.rollback()
            logger.error(f"فشل في تطبيق migration 4: {e}")
            raise

async def run_migrations():
    """تشغيل جميع المigrations المطلوبة"""
    await init_migrations_table()
    current_version = await get_current_schema_version()
    
    logger.info(f"إصدار قاعدة البيانات الحالي: {current_version}")
    
    # قائمة المigrations المطلوبة
    migrations = [
        (1, migration_v1_services_and_categories),
        (2, migration_v2_pricing_rules),
        (3, migration_v3_crypto_system),
        (4, migration_v4_enhanced_deposits),
    ]
    
    for version, migration_func in migrations:
        if current_version < version:
            logger.info(f"تطبيق migration {version}...")
            await migration_func()
        else:
            logger.info(f"Migration {version} مطبق بالفعل")
    
    logger.info("اكتمل تطبيق جميع المigrations")

async def reset_database():
    """إعادة تعيين قاعدة البيانات (للتطوير فقط)"""
    logger.warning("تحذير: إعادة تعيين قاعدة البيانات!")
    async with aiosqlite.connect(config.DB_NAME) as db:
        # حذف جميع الجداول
        tables = [
            'schema_migrations', 'crypto_transactions', 'crypto_wallets',
            'pricing_rules', 'services', 'categories', 'deposits', 'orders', 'ranks', 'users'
        ]
        
        for table in tables:
            try:
                await db.execute(f"DROP TABLE IF EXISTS {table}")
            except Exception as e:
                logger.error(f"خطأ في حذف جدول {table}: {e}")
        
        await db.commit()
        logger.info("تم حذف جميع الجداول")