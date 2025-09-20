"""
نقطة بدء البوت الرئيسية
"""

import asyncio
import logging
import logging.config
import os
import signal
import sys
from datetime import datetime

import aiosqlite
from aiogram import Dispatcher

import config
from bot import bot, dp, cleanup_resources, start_order_updater
from database import init_all_db
from handlers import admin_router, user_router
from utils.common import setup_logging

# إعداد نظام التسجيل
logger = setup_logging("smm_bot")

# التحقق من وجود ملف القفل وإزالته إذا كان موجودًا
LOCK_FILE = "bot.lock"
if os.path.exists(LOCK_FILE):
    try:
        os.remove(LOCK_FILE)
        logger.warning(f"تم إزالة ملف القفل القديم: {LOCK_FILE}")
    except Exception as e:
        logger.error(f"فشل في إزالة ملف القفل: {e}")

# إنشاء ملف قفل جديد
try:
    with open(LOCK_FILE, "w") as lock_file:
        lock_file.write(f"{datetime.now().isoformat()}\n")
except Exception as e:
    logger.error(f"فشل في إنشاء ملف القفل: {e}")

# إعداد معالج إشارات للإغلاق النظيف
def signal_handler(sig, frame):
    """معالج الإشارات"""
    logger.info(f"تم استلام إشارة الإيقاف: {sig}")
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
            logger.info(f"تم إزالة ملف القفل: {LOCK_FILE}")
        except Exception as e:
            logger.error(f"فشل في إزالة ملف القفل: {e}")
    sys.exit(0)

# تسجيل معالجات الإشارات
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# تعريف دالة بدء البوت
async def main():
    """دالة بدء البوت الرئيسية"""
    try:
        # تهيئة قاعدة البيانات
        logger.info("بدء تهيئة قاعدة البيانات...")
        await init_all_db()
        logger.info("اكتملت تهيئة قاعدة البيانات")

        # تسجيل الموجهات في الموزع
        dp.include_router(admin_router)
        dp.include_router(user_router)
        
        # إضافة موجه التسعير
        from handlers import pricing_router
        dp.include_router(pricing_router)
        
        # بدء مهمة تحديث حالة الطلبات
        logger.info("جاري بدء مهمة تحديث حالة الطلبات...")
        await start_order_updater()

        # بدء استقبال التحديثات
        logger.info(f"بدء تشغيل البوت: @{(await bot.get_me()).username}")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"فشل في بدء البوت: {e}")
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        raise
    finally:
        # تنظيف الموارد
        await cleanup_resources()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

# تشغيل البوت
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("تم إيقاف البوت")
    except Exception as e:
        logger.critical(f"خطأ غير متوقع: {e}")
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)