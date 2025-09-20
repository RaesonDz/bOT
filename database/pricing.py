"""
وحدة نظام التسعير الديناميكي

يدير قواعد التسعير بالنسب والرسوم الثابتة حسب المستخدم والخدمة والفئة
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

# ذاكرة التخزين المؤقت للقواعد
_pricing_rules_cache = {}
_cache_expiry = None

async def init_pricing_tables():
    """تهيئة جداول التسعير"""
    # لا نحتاج لتشغيل migrations هنا لأنها تتم في init_all_db()
    pass

async def create_pricing_rule(name: str, scope: str, ref_id: int = None, 
                            rank_id: int = None, percentage: float = 0, 
                            fixed_fee: float = 0, created_by: int = None,
                            starts_at: str = None, ends_at: str = None) -> int:
    """إنشاء قاعدة تسعير جديدة"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            cursor = await db.execute(
                """INSERT INTO pricing_rules (name, scope, ref_id, rank_id, percentage, 
                   fixed_fee, created_by, starts_at, ends_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, scope, ref_id, rank_id, percentage, fixed_fee, 
                 created_by, starts_at, ends_at)
            )
            await db.commit()
            rule_id = cursor.lastrowid
            
            # إلغاء ذاكرة التخزين المؤقت
            await invalidate_pricing_cache()
            
            logger.info(f"تم إنشاء قاعدة تسعير جديدة: {rule_id} - {name}")
            return rule_id
    except Exception as e:
        logger.error(f"خطأ في إنشاء قاعدة التسعير {name}: {e}")
        return -1

async def get_pricing_rules(scope: str = None, ref_id: int = None, 
                          rank_id: int = None, active_only: bool = True) -> List[Dict[str, Any]]:
    """الحصول على قواعد التسعير"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            query = "SELECT * FROM pricing_rules WHERE 1=1"
            params = []
            
            if active_only:
                query += " AND is_active = 1"
                query += " AND (starts_at IS NULL OR starts_at <= CURRENT_TIMESTAMP)"
                query += " AND (ends_at IS NULL OR ends_at >= CURRENT_TIMESTAMP)"
            
            if scope:
                query += " AND scope = ?"
                params.append(scope)
            
            if ref_id is not None:
                query += " AND ref_id = ?"
                params.append(ref_id)
            
            if rank_id is not None:
                query += " AND rank_id = ?"
                params.append(rank_id)
            
            query += " ORDER BY scope DESC, rank_id ASC"
            
            cursor = await db.execute(query, params)
            rules = await cursor.fetchall()
            
            return [dict(rule) for rule in rules]
    except Exception as e:
        logger.error(f"خطأ في جلب قواعد التسعير: {e}")
        return []

async def calculate_service_price(service_id: int, base_price: float, 
                                user_rank_id: int = 6, category_id: int = None) -> Dict[str, Any]:
    """حساب السعر النهائي للخدمة حسب قواعد التسعير وخصومات الرتب"""
    try:
        # أولاً، الحصول على خصم الرتبة من نظام الرتب الجديد
        from database.ranks import get_rank_by_id
        
        rank_info = await get_rank_by_id(user_rank_id)
        rank_discount = rank_info.get('discount_percentage', 0.0)
        
        # الحصول على قواعد التسعير مع الأولوية
        # الأولوية: خدمة+رتبة > خدمة > فئة+رتبة > فئة > عام+رتبة > عام
        
        final_price = base_price
        applied_rules = []
        total_percentage = 0
        total_fixed_fee = 0
        
        # تطبيق خصم الرتبة أولاً
        if rank_discount > 0:
            # خصم الرتبة يُطبق كخصم (نسبة سالبة)
            total_percentage -= rank_discount
            applied_rules.append({
                'id': f'rank_{user_rank_id}',
                'name': f'خصم رتبة {rank_info.get("name", "غير محدد")}',
                'scope': 'rank_discount',
                'percentage': -rank_discount,
                'fixed_fee': 0
            })
        
        # البحث عن القواعد بترتيب الأولوية
        rule_priorities = [
            ('service', service_id, user_rank_id),  # خدمة محددة + رتبة
            ('service', service_id, None),          # خدمة محددة
            ('category', category_id, user_rank_id) if category_id else None,  # فئة + رتبة
            ('category', category_id, None) if category_id else None,          # فئة
            ('global', None, user_rank_id),         # عام + رتبة
            ('global', None, None),                 # عام
        ]
        
        # تطبيق أول قاعدة متطابقة لكل مستوى
        for priority in rule_priorities:
            if priority is None:
                continue
                
            scope, ref_id, rank_id = priority
            rules = await get_pricing_rules(scope=scope, ref_id=ref_id, rank_id=rank_id)
            
            if rules:
                # تطبيق أول قاعدة نشطة
                rule = rules[0]
                total_percentage += rule.get('percentage', 0)
                total_fixed_fee += rule.get('fixed_fee', 0)
                applied_rules.append({
                    'id': rule['id'],
                    'name': rule['name'],
                    'scope': rule['scope'],
                    'percentage': rule['percentage'],
                    'fixed_fee': rule['fixed_fee']
                })
                break  # تطبيق أول قاعدة فقط حسب الأولوية
        
        # حساب السعر النهائي
        if total_percentage != 0:
            final_price = base_price * (1 + total_percentage / 100)
        
        final_price += total_fixed_fee
        final_price = round(final_price, 4)
        
        result = {
            'base_price': base_price,
            'final_price': final_price,
            'total_percentage': total_percentage,
            'total_fixed_fee': total_fixed_fee,
            'applied_rules': applied_rules,
            'savings': base_price - final_price if final_price < base_price else 0,
            'rank_discount': rank_discount,
            'rank_name': rank_info.get('name', 'غير محدد')
        }
        
        logger.debug(f"حساب سعر الخدمة {service_id}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"خطأ في حساب سعر الخدمة {service_id}: {e}")
        return {
            'base_price': base_price,
            'final_price': base_price,
            'total_percentage': 0,
            'total_fixed_fee': 0,
            'applied_rules': [],
            'savings': 0,
            'rank_discount': 0.0,
            'rank_name': 'غير محدد'
        }

async def get_pricing_preview(user_rank_id: int = 6) -> Dict[str, Any]:
    """معاينة التسعير لجميع الخدمات حسب رتبة المستخدم"""
    try:
        from database.services import get_services, get_categories
        
        categories = await get_categories()
        preview = {'categories': [], 'total_services': 0, 'total_savings': 0}
        
        for category in categories:
            category_data = {
                'id': category['id'],
                'name': category['name'],
                'services': [],
                'category_savings': 0
            }
            
            services = await get_services(category_id=category['id'])
            
            for service in services:
                pricing = await calculate_service_price(
                    service_id=service['id'],
                    base_price=service['base_price'],
                    user_rank_id=user_rank_id,
                    category_id=category['id']
                )
                
                service_data = {
                    'id': service['id'],
                    'name': service['name'],
                    'base_price': pricing['base_price'],
                    'final_price': pricing['final_price'],
                    'savings': pricing['savings'],
                    'applied_rules': pricing['applied_rules']
                }
                
                category_data['services'].append(service_data)
                category_data['category_savings'] += pricing['savings']
                preview['total_savings'] += pricing['savings']
            
            preview['categories'].append(category_data)
            preview['total_services'] += len(services)
        
        return preview
        
    except Exception as e:
        logger.error(f"خطأ في معاينة التسعير: {e}")
        return {'categories': [], 'total_services': 0, 'total_savings': 0}

async def update_pricing_rule(rule_id: int, name: str = None, percentage: float = None,
                            fixed_fee: float = None, is_active: bool = None,
                            starts_at: str = None, ends_at: str = None) -> bool:
    """تحديث قاعدة تسعير"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            # بناء استعلام التحديث ديناميكياً
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            
            if percentage is not None:
                updates.append("percentage = ?")
                params.append(percentage)
            
            if fixed_fee is not None:
                updates.append("fixed_fee = ?")
                params.append(fixed_fee)
            
            if is_active is not None:
                updates.append("is_active = ?")
                params.append(is_active)
            
            if starts_at is not None:
                updates.append("starts_at = ?")
                params.append(starts_at)
            
            if ends_at is not None:
                updates.append("ends_at = ?")
                params.append(ends_at)
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(rule_id)
            
            query = f"UPDATE pricing_rules SET {', '.join(updates)} WHERE id = ?"
            await db.execute(query, params)
            await db.commit()
            
            # إلغاء ذاكرة التخزين المؤقت
            await invalidate_pricing_cache()
            
            logger.info(f"تم تحديث قاعدة التسعير {rule_id}")
            return True
    except Exception as e:
        logger.error(f"خطأ في تحديث قاعدة التسعير {rule_id}: {e}")
        return False

async def delete_pricing_rule(rule_id: int) -> bool:
    """حذف قاعدة تسعير"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            await db.execute("DELETE FROM pricing_rules WHERE id = ?", (rule_id,))
            await db.commit()
            
            # إلغاء ذاكرة التخزين المؤقت
            await invalidate_pricing_cache()
            
            logger.info(f"تم حذف قاعدة التسعير {rule_id}")
            return True
    except Exception as e:
        logger.error(f"خطأ في حذف قاعدة التسعير {rule_id}: {e}")
        return False

async def get_pricing_rule_by_id(rule_id: int) -> Optional[Dict[str, Any]]:
    """الحصول على قاعدة تسعير بواسطة المعرف"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            cursor = await db.execute("SELECT * FROM pricing_rules WHERE id = ?", (rule_id,))
            rule = await cursor.fetchone()
            
            return dict(rule) if rule else None
    except Exception as e:
        logger.error(f"خطأ في جلب قاعدة التسعير {rule_id}: {e}")
        return None

async def invalidate_pricing_cache():
    """إلغاء ذاكرة التخزين المؤقت للتسعير"""
    global _pricing_rules_cache, _cache_expiry
    _pricing_rules_cache.clear()
    _cache_expiry = None
    logger.debug("تم إلغاء ذاكرة التخزين المؤقت للتسعير")

async def get_pricing_statistics() -> Dict[str, Any]:
    """الحصول على إحصائيات التسعير"""
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            db.row_factory = sqlite3.Row
            
            # عدد القواعد النشطة
            cursor = await db.execute(
                "SELECT COUNT(*) as count FROM pricing_rules WHERE is_active = 1"
            )
            active_rules = (await cursor.fetchone())['count']
            
            # عدد القواعد حسب النطاق
            cursor = await db.execute(
                """SELECT scope, COUNT(*) as count 
                   FROM pricing_rules WHERE is_active = 1 
                   GROUP BY scope"""
            )
            scope_stats = {row['scope']: row['count'] for row in await cursor.fetchall()}
            
            # متوسط النسبة المئوية
            cursor = await db.execute(
                "SELECT AVG(percentage) as avg_percentage FROM pricing_rules WHERE is_active = 1"
            )
            avg_percentage = (await cursor.fetchone())['avg_percentage'] or 0
            
            return {
                'active_rules': active_rules,
                'scope_stats': scope_stats,
                'average_percentage': round(avg_percentage, 2)
            }
    except Exception as e:
        logger.error(f"خطأ في جلب إحصائيات التسعير: {e}")
        return {'active_rules': 0, 'scope_stats': {}, 'average_percentage': 0}