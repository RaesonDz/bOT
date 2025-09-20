
"""
حزمة قاعدة البيانات
"""

from database.core import init_db
from database.deposit import init_deposit_tables
from database.ranks import init_ranks

async def init_all_db():
    """تهيئة جميع عناصر قاعدة البيانات"""
    await init_db()
    await init_deposit_tables()
    await init_ranks()
