
"""
حزمة قاعدة البيانات
"""

from database.core import init_db
from database.deposit import init_deposit_tables
from database.ranks import init_ranks
from database.migrations import run_migrations
from database.services import init_services_tables
from database.pricing import init_pricing_tables
from database.crypto import init_crypto_tables

async def init_all_db():
    """تهيئة جميع عناصر قاعدة البيانات"""
    # تهيئة الجداول الأساسية أولاً
    await init_db()
    await init_deposit_tables()
    await init_ranks()
    
    # تشغيل جميع المigrations مرة واحدة فقط
    await run_migrations()
    
    # الآن جميع الجداول جاهزة ولا نحتاج لاستدعاءات إضافية
