"""
ملف إعداد البوت الرئيسي
"""

import logging
import sys
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

import config
from utils.common import setup_logging

# إنشاء مسجل
logger = setup_logging("smm_bot")

# إنشاء كائن البوت مع الإعدادات الافتراضية
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# إنشاء موزع مع تخزين الحالة في الذاكرة
dp = Dispatcher(storage=MemoryStorage())

# تخزين المهام الخلفية
background_tasks = {}

# دالة لبدء التحديث الدوري لحالة الطلبات
async def start_order_updater():
    """بدء مهمة تحديث حالة الطلبات بشكل دوري"""
    try:
        from utils.order_status_updater import schedule_order_status_updater
        
        # إنشاء قاموس للتطبيق لتخزين المهام الخلفية
        app = {}
        await schedule_order_status_updater(app)
        
        # تخزين المهمة في المتغير العام لمنع جامع المهملات من حذفها
        background_tasks["order_updater"] = app.get("order_status_task")
        
        logger.info("تم بدء محدث حالة الطلبات بنجاح")
    except Exception as e:
        logger.error(f"فشل بدء محدث حالة الطلبات: {e}")

# دالة لتنظيف الموارد عند إغلاق البوت
async def cleanup_resources():
    """تنظيف الموارد عند إغلاق البوت"""
    logger.info("بدء تنظيف الموارد...")

    try:
        # إغلاق جلسة API إذا كانت موجودة
        from services.api import close_api_session
        await close_api_session()
        logger.info("تم إغلاق جلسة API")
    except Exception as e:
        logger.error(f"خطأ أثناء إغلاق جلسة API: {e}")

    # إلغاء المهام الخلفية
    try:
        for task_name, task in background_tasks.items():
            if task and not task.done():
                logger.info(f"إلغاء المهمة الخلفية: {task_name}")
                task.cancel()
        logger.info("تم إلغاء المهام الخلفية")
    except Exception as e:
        logger.error(f"خطأ في إلغاء المهام الخلفية: {e}")

    # إغلاق جلسة البوت
    try:
        if hasattr(bot, 'session') and bot.session:
            await bot.session.close()
            logger.info("تم إغلاق جلسة البوت")
    except Exception as e:
        logger.error(f"خطأ أثناء إغلاق جلسة البوت: {e}")

    # إغلاق المهام المعلقة
    try:
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            logger.info(f"إلغاء {len(tasks)} مهمة معلقة")
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("اكتمل تنظيف الموارد")
    except Exception as e:
        logger.error(f"خطأ في إلغاء المهام المعلقة: {e}")