"""
وحدة إدارة الخدمات والفئات
"""

import logging
import sqlite3
import aiosqlite
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import config

# إعداد المسجل
logger = logging.getLogger("smm_bot")

async def init_services_tables():
    """تهيئة جداول الخدمات والفئات"""
    # لا نحتاج لتشغيل migrations هنا لأنها تتم في init_all_db()
    pass

async def create_category(name: str, description: str = None, visibility_min_rank: int = 5) -> int:
    """إنشاء فئة جديدة"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            cursor = await db.execute(
                """INSERT INTO categories (name, description, visibility_min_rank) 
                   VALUES (?, ?, ?)""",
                (name, description, visibility_min_rank)
            )
            await db.commit()
            category_id = cursor.lastrowid
            logger.info(f"تم إنشاء فئة جديدة: {category_id} - {name}")
            return category_id
    except Exception as e:
        logger.error(f"خطأ في إنشاء فئة {name}: {e}")
        return -1

async def get_categories(include_inactive: bool = False, min_rank: int = 5) -> List[Dict[str, Any]]:
    """الحصول على قائمة الفئات"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            query = "SELECT * FROM categories WHERE 1=1"
            params = []
            
            if not include_inactive:
                query += " AND is_active = 1"
            
            query += " AND visibility_min_rank >= ?"
            params.append(min_rank)
            
            query += " ORDER BY display_order ASC, name ASC"
            
            cursor = await db.execute(query, params)
            categories = await cursor.fetchall()
            
            return [dict(category) for category in categories]
    except Exception as e:
        logger.error(f"خطأ في جلب الفئات: {e}")
        return []

async def create_or_update_service(external_id: int, category_id: int, name: str, 
                                 base_price: float, min_quantity: int = 1, 
                                 max_quantity: int = 10000, description: str = None,
                                 raw_api_data: dict = None) -> int:
    """إنشاء أو تحديث خدمة"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            # فحص إذا كانت الخدمة موجودة
            cursor = await db.execute(
                "SELECT id FROM services WHERE external_id = ?", (external_id,)
            )
            existing = await cursor.fetchone()
            
            raw_data_json = json.dumps(raw_api_data) if raw_api_data else None
            
            if existing:
                # تحديث الخدمة الموجودة
                await db.execute(
                    """UPDATE services SET category_id = ?, name = ?, base_price = ?, 
                       min_quantity = ?, max_quantity = ?, description = ?, 
                       raw_api_data = ?, updated_at = CURRENT_TIMESTAMP 
                       WHERE external_id = ?""",
                    (category_id, name, base_price, min_quantity, max_quantity, 
                     description, raw_data_json, external_id)
                )
                service_id = existing[0]
                logger.info(f"تم تحديث الخدمة: {service_id} - {name}")
            else:
                # إنشاء خدمة جديدة
                cursor = await db.execute(
                    """INSERT INTO services (external_id, category_id, name, base_price, 
                       min_quantity, max_quantity, description, raw_api_data) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (external_id, category_id, name, base_price, min_quantity, 
                     max_quantity, description, raw_data_json)
                )
                service_id = cursor.lastrowid
                logger.info(f"تم إنشاء خدمة جديدة: {service_id} - {name}")
            
            await db.commit()
            return service_id
    except Exception as e:
        logger.error(f"خطأ في إنشاء/تحديث الخدمة {name}: {e}")
        return -1

async def get_services(category_id: int = None, include_inactive: bool = False, 
                      min_rank: int = 5) -> List[Dict[str, Any]]:
    """الحصول على قائمة الخدمات"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            query = """
            SELECT s.*, c.name as category_name 
            FROM services s 
            LEFT JOIN categories c ON s.category_id = c.id 
            WHERE 1=1
            """
            params = []
            
            if category_id:
                query += " AND s.category_id = ?"
                params.append(category_id)
            
            if not include_inactive:
                query += " AND s.is_active = 1 AND c.is_active = 1"
            
            query += " AND s.visibility_min_rank >= ?"
            params.append(min_rank)
            
            query += " ORDER BY c.display_order ASC, s.name ASC"
            
            cursor = await db.execute(query, params)
            services = await cursor.fetchall()
            
            result = []
            for service in services:
                service_dict = dict(service)
                # تحليل البيانات الخام إذا كانت موجودة
                if service_dict.get('raw_api_data'):
                    try:
                        service_dict['raw_api_data'] = json.loads(service_dict['raw_api_data'])
                    except:
                        service_dict['raw_api_data'] = None
                result.append(service_dict)
            
            return result
    except Exception as e:
        logger.error(f"خطأ في جلب الخدمات: {e}")
        return []

async def get_service_by_id(service_id: int) -> Optional[Dict[str, Any]]:
    """الحصول على خدمة بواسطة المعرف"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            cursor = await db.execute(
                """SELECT s.*, c.name as category_name 
                   FROM services s 
                   LEFT JOIN categories c ON s.category_id = c.id 
                   WHERE s.id = ?""",
                (service_id,)
            )
            service = await cursor.fetchone()
            
            if service:
                service_dict = dict(service)
                if service_dict.get('raw_api_data'):
                    try:
                        service_dict['raw_api_data'] = json.loads(service_dict['raw_api_data'])
                    except:
                        service_dict['raw_api_data'] = None
                return service_dict
            return None
    except Exception as e:
        logger.error(f"خطأ في جلب الخدمة {service_id}: {e}")
        return None

async def get_service_by_external_id(external_id: int) -> Optional[Dict[str, Any]]:
    """الحصول على خدمة بواسطة المعرف الخارجي"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            cursor = await db.execute(
                """SELECT s.*, c.name as category_name 
                   FROM services s 
                   LEFT JOIN categories c ON s.category_id = c.id 
                   WHERE s.external_id = ?""",
                (external_id,)
            )
            service = await cursor.fetchone()
            
            if service:
                service_dict = dict(service)
                if service_dict.get('raw_api_data'):
                    try:
                        service_dict['raw_api_data'] = json.loads(service_dict['raw_api_data'])
                    except:
                        service_dict['raw_api_data'] = None
                return service_dict
            return None
    except Exception as e:
        logger.error(f"خطأ في جلب الخدمة {external_id}: {e}")
        return None

async def update_service_visibility(service_id: int, is_active: bool, visibility_min_rank: int = None) -> bool:
    """تحديث ظهور الخدمة"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            if visibility_min_rank is not None:
                await db.execute(
                    "UPDATE services SET is_active = ?, visibility_min_rank = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (is_active, visibility_min_rank, service_id)
                )
            else:
                await db.execute(
                    "UPDATE services SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (is_active, service_id)
                )
            await db.commit()
            logger.info(f"تم تحديث ظهور الخدمة {service_id}: active={is_active}")
            return True
    except Exception as e:
        logger.error(f"خطأ في تحديث ظهور الخدمة {service_id}: {e}")
        return False

async def update_category_visibility(category_id: int, is_active: bool, visibility_min_rank: int = None) -> bool:
    """تحديث ظهور الفئة"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            if visibility_min_rank is not None:
                await db.execute(
                    "UPDATE categories SET is_active = ?, visibility_min_rank = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (is_active, visibility_min_rank, category_id)
                )
            else:
                await db.execute(
                    "UPDATE categories SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (is_active, category_id)
                )
            await db.commit()
            logger.info(f"تم تحديث ظهور الفئة {category_id}: active={is_active}")
            return True
    except Exception as e:
        logger.error(f"خطأ في تحديث ظهور الفئة {category_id}: {e}")
        return False

async def sync_services_from_api(api_services: List[Dict]) -> Dict[str, int]:
    """مزامنة الخدمات من API الخارجي"""
    stats = {"created": 0, "updated": 0, "errors": 0}
    
    try:
        # إنشاء فئة افتراضية إذا لم تكن موجودة
        default_category_id = await create_category("خدمات عامة", "الفئة الافتراضية للخدمات")
        if default_category_id == -1:
            # محاولة العثور على فئة موجودة
            categories = await get_categories(include_inactive=True)
            if categories:
                default_category_id = categories[0]['id']
            else:
                logger.error("لا يمكن إنشاء أو العثور على فئة افتراضية")
                return stats
        
        for service_data in api_services:
            try:
                external_id = service_data.get('service')
                name = service_data.get('name', f'خدمة {external_id}')
                price = float(service_data.get('rate', 0))
                min_qty = int(service_data.get('min', 1))
                max_qty = int(service_data.get('max', 10000))
                category = service_data.get('category', 'عام')
                
                # البحث عن فئة مناسبة أو إنشاؤها
                category_id = default_category_id
                categories = await get_categories(include_inactive=True)
                for cat in categories:
                    if cat['name'].lower() == category.lower():
                        category_id = cat['id']
                        break
                else:
                    # إنشاء فئة جديدة
                    new_cat_id = await create_category(category)
                    if new_cat_id != -1:
                        category_id = new_cat_id
                
                # إنشاء أو تحديث الخدمة
                service_id = await create_or_update_service(
                    external_id=external_id,
                    category_id=category_id,
                    name=name,
                    base_price=price,
                    min_quantity=min_qty,
                    max_quantity=max_qty,
                    raw_api_data=service_data
                )
                
                if service_id != -1:
                    # فحص إذا كانت خدمة جديدة أم محدثة
                    existing = await get_service_by_external_id(external_id)
                    if existing and existing['id'] == service_id:
                        stats["updated"] += 1
                    else:
                        stats["created"] += 1
                else:
                    stats["errors"] += 1
                    
            except Exception as e:
                logger.error(f"خطأ في مزامنة خدمة {service_data}: {e}")
                stats["errors"] += 1
        
        logger.info(f"اكتملت مزامنة الخدمات: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"خطأ في مزامنة الخدمات: {e}")
        stats["errors"] += 1
        return stats