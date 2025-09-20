"""
مزامنة الخدمات والفئات من API
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple

import aiosqlite

from services.api import get_services, organize_services_by_category, init_api_session, close_api_session

# إعداد التسجيل
logger = logging.getLogger("smm_bot")

# الحصول على مسار قاعدة البيانات
DB_PATH = os.getenv("DATABASE_PATH", "database.db")

async def sync_categories_from_api() -> Tuple[int, int, int]:
    """
    مزامنة الفئات من API وحفظها في قاعدة البيانات
    
    Returns:
        Tuple[int, int, int]: (إجمالي الفئات التي تمت مزامنتها، عدد الفئات الجديدة، عدد الفئات التي تم تحديثها)
    """
    try:
        # الحصول على قائمة الخدمات من API
        services_list = await get_services()
        
        # إذا كانت القائمة فارغة، سجل خطأ وعد
        if not services_list:
            logger.error("لم يتم الحصول على خدمات من API")
            return 0, 0, 0
        
        # تنظيم الخدمات حسب الفئة
        categories_dict = organize_services_by_category(services_list)
        
        # عدادات للإحصائيات
        total_categories = len(categories_dict)
        new_categories = 0
        updated_categories = 0
        
        # افتح اتصالًا بقاعدة البيانات
        async with aiosqlite.connect(DB_PATH) as db:
            # تحويل كائن الاتصال لاستخدام القواميس
            db.row_factory = aiosqlite.Row
            
            # الحصول على قائمة الفئات الموجودة في قاعدة البيانات
            async with db.execute("SELECT name FROM categories") as cursor:
                existing_categories = {row['name']: True for row in await cursor.fetchall()}
            
            # إنشاء فئات جديدة وتحديث الموجودة
            for i, (category_name, services) in enumerate(categories_dict.items()):
                try:
                    # التحقق مما إذا كانت الفئة موجودة بالفعل
                    if category_name in existing_categories:
                        # تحديث الفئة الحالية (فقط ترتيب العرض)
                        await db.execute(
                            "UPDATE categories SET order_num = ? WHERE name = ?",
                            (i, category_name)
                        )
                        updated_categories += 1
                    else:
                        # إدراج فئة جديدة
                        await db.execute(
                            """
                            INSERT INTO categories (name, description, order_num)
                            VALUES (?, ?, ?)
                            """,
                            (category_name, f"خدمات {category_name}", i)
                        )
                        new_categories += 1
                except Exception as e:
                    logger.error(f"خطأ أثناء مزامنة الفئة {category_name}: {e}")
            
            # حفظ التغييرات
            await db.commit()
            
        logger.info(f"تمت مزامنة {total_categories} فئة: {new_categories} جديدة، {updated_categories} محدثة")
        return total_categories, new_categories, updated_categories
    
    except Exception as e:
        logger.error(f"خطأ أثناء مزامنة الفئات: {e}")
        return 0, 0, 0

async def sync_services_from_api() -> Tuple[int, int, int]:
    """
    مزامنة الخدمات من API وحفظها في قاعدة البيانات
    
    Returns:
        Tuple[int, int, int]: (إجمالي الخدمات التي تمت مزامنتها، عدد الخدمات الجديدة، عدد الخدمات التي تم تحديثها)
    """
    try:
        # الحصول على قائمة الخدمات من API
        services_list = await get_services()
        
        # إذا كانت القائمة فارغة، سجل خطأ وعد
        if not services_list:
            logger.error("لم يتم الحصول على خدمات من API")
            return 0, 0, 0
        
        # عدادات للإحصائيات
        total_services = len(services_list)
        new_services = 0
        updated_services = 0
        
        # الوقت الحالي لتحديث آخر مزامنة
        current_time = datetime.now().isoformat()
        
        # افتح اتصالًا بقاعدة البيانات
        async with aiosqlite.connect(DB_PATH) as db:
            # تحويل كائن الاتصال لاستخدام القواميس
            db.row_factory = aiosqlite.Row
            
            # الحصول على قائمة الخدمات الموجودة في قاعدة البيانات
            async with db.execute("SELECT service_id FROM services") as cursor:
                existing_services = {row['service_id']: True for row in await cursor.fetchall()}
            
            # إنشاء خدمات جديدة وتحديث الموجودة
            for service in services_list:
                try:
                    service_id = service.get('service')
                    if not service_id:
                        logger.warning(f"تم تخطي خدمة بدون معرف: {service}")
                        continue
                    
                    # تحويل القيم وضمان أنها تتناسب مع أنواع البيانات المتوقعة
                    service_name = service.get('name', '')
                    service_type = service.get('type', '')
                    category = service.get('category', 'أخرى')
                    
                    # التعامل مع القيم الرقمية بشكل آمن
                    try:
                        rate = float(service.get('rate', 0))
                        min_order = int(service.get('min', 0))
                        max_order = int(service.get('max', 0))
                    except (ValueError, TypeError):
                        rate = 0.0
                        min_order = 0
                        max_order = 0
                    
                    # تحويل القيم المنطقية
                    refill = 1 if service.get('refill', False) else 0
                    cancel = 1 if service.get('cancel', False) else 0
                    
                    # وصف الخدمة (قد يكون فارغًا)
                    description = service.get('description', '')
                    
                    # التحقق مما إذا كانت الخدمة موجودة بالفعل
                    if service_id in existing_services:
                        # تحديث الخدمة الحالية
                        await db.execute(
                            """
                            UPDATE services
                            SET name = ?, type = ?, category = ?, rate = ?, min = ?, max = ?,
                                refill = ?, cancel = ?, description = ?, last_updated = ?
                            WHERE service_id = ?
                            """,
                            (service_name, service_type, category, rate, min_order, max_order,
                             refill, cancel, description, current_time, service_id)
                        )
                        updated_services += 1
                    else:
                        # إدراج خدمة جديدة
                        await db.execute(
                            """
                            INSERT INTO services
                            (service_id, name, type, category, rate, min, max, refill, cancel, description, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (service_id, service_name, service_type, category, rate, min_order, max_order,
                             refill, cancel, description, current_time)
                        )
                        new_services += 1
                except Exception as e:
                    logger.error(f"خطأ أثناء مزامنة الخدمة {service.get('service', 'غير معروف')}: {e}")
            
            # حفظ التغييرات
            await db.commit()
            
        logger.info(f"تمت مزامنة {total_services} خدمة: {new_services} جديدة، {updated_services} محدثة")
        return total_services, new_services, updated_services
    
    except Exception as e:
        logger.error(f"خطأ أثناء مزامنة الخدمات: {e}")
        return 0, 0, 0

async def sync_all() -> Dict[str, Any]:
    """
    مزامنة الفئات والخدمات من API
    
    Returns:
        Dict[str, Any]: إحصائيات المزامنة
    """
    try:
        # تهيئة جلسة API
        await init_api_session()
        
        # مزامنة الفئات أولاً
        categories_stats = await sync_categories_from_api()
        
        # ثم مزامنة الخدمات
        services_stats = await sync_services_from_api()
        
        # إغلاق جلسة API
        await close_api_session()
        
        # إرجاع إحصائيات المزامنة
        return {
            "categories": {
                "total": categories_stats[0],
                "new": categories_stats[1],
                "updated": categories_stats[2]
            },
            "services": {
                "total": services_stats[0],
                "new": services_stats[1],
                "updated": services_stats[2]
            },
            "success": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"خطأ أثناء المزامنة الشاملة: {e}")
        # إغلاق جلسة API في حالة حدوث خطأ
        await close_api_session()
        
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# لاختبار الوظيفة عند تشغيل الملف مباشرة
if __name__ == "__main__":
    import sys
    
    async def test_sync():
        result = await sync_all()
        print(f"نتيجة المزامنة: {result}")
        
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(test_sync())