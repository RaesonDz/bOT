"""
وحدة تحديث حالة الطلبات بشكل دوري

هذه الوحدة مسؤولة عن تحديث حالة طلبات البوت بشكل دوري من خلال:
1. استرجاع الطلبات النشطة من قاعدة البيانات
2. استرجاع حالتها من API الخارجية
3. تحديث حالتها في قاعدة البيانات المحلية
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
import time

from database.core import (
    get_all_orders,
    update_order_status,
    update_order_remains_simple
)
from database.ranks import increment_user_purchases_and_check_rank
from services.api import (
    check_order_status,
    check_multiple_orders
)

# إعداد المسجل
logger = logging.getLogger("smm_bot")

# المدة الزمنية بين دورات التحديث بالثواني
UPDATE_INTERVAL = 300  # 5 دقائق
# عدد الطلبات في كل دفعة لطلبات API المتعددة
BATCH_SIZE = 50

# قاموس حالات طلبات API المختلفة وما يقابلها في قاعدة البيانات
API_STATUS_MAPPING = {
    "pending": "pending",
    "in progress": "in_progress",
    "processing": "processing",
    "partial": "partial",
    "completed": "completed",
    "canceled": "canceled",
    "refunded": "refunded",
    "failed": "failed"
}

async def convert_api_status(api_status: str) -> str:
    """
    تحويل حالة الطلب من صيغة API إلى صيغة قاعدة البيانات المحلية
    
    Args:
        api_status: حالة الطلب كما هي من API
        
    Returns:
        str: حالة الطلب بالصيغة المستخدمة في قاعدة البيانات المحلية
    """
    if not api_status:
        return "pending"
    
    # تنظيف الحالة: تحويل إلى أحرف صغيرة وإزالة المسافات الزائدة
    cleaned_status = api_status.lower().strip()
    
    # استبدال المسافات بالشرطات السفلية للاتساق مع نظام قاعدة البيانات
    cleaned_status = cleaned_status.replace(" ", "_")
    
    # إعادة اسم الحالة المعروف أو الافتراضي
    return API_STATUS_MAPPING.get(cleaned_status, cleaned_status)

async def get_active_orders() -> List[Dict[str, Any]]:
    """
    الحصول على الطلبات النشطة التي تحتاج إلى تحديث
    
    Returns:
        List[Dict[str, Any]]: قائمة بالطلبات النشطة
    """
    try:
        # استرجاع الطلبات التي ليست في حالة مكتملة أو ملغاة
        active_statuses = ["pending", "in_progress", "processing"]
        orders, _ = await get_all_orders(status=None)  # نسترجع كل الطلبات ثم نقوم بالتصفية
        
        active_orders = []
        for order in orders:
            status = order.get("status", "").lower()
            # نضيف الطلب إذا كان في إحدى الحالات النشطة
            if status in active_statuses:
                active_orders.append(order)
        
        logger.info(f"تم استرجاع {len(active_orders)} طلب نشط للتحديث")
        return active_orders
    except Exception as e:
        logger.error(f"خطأ في استرجاع الطلبات النشطة: {e}")
        return []

async def update_single_order(order: Dict[str, Any]) -> bool:
    """
    تحديث حالة طلب واحد
    
    Args:
        order: بيانات الطلب
        
    Returns:
        bool: True إذا تم التحديث بنجاح، False خلاف ذلك
    """
    try:
        order_id = order.get("order_id")
        
        if not order_id:
            logger.warning(f"طلب بدون معرف: {order}")
            return False
        
        # طلب محلي فقط، لا يمكن تحديثه من API
        if str(order_id).startswith("LOCAL-"):
            logger.debug(f"تخطي الطلب المحلي: {order_id}")
            return False
        
        # الحصول على حالة الطلب من API
        api_response = await check_order_status(order_id)
        
        if "error" in api_response:
            logger.warning(f"خطأ في تحديث الطلب {order_id}: {api_response['error']}")
            return False
        
        # استخراج البيانات من استجابة API
        api_status = api_response.get("status", "")
        remains = api_response.get("remains", "0")
        
        # تحويل البيانات إلى الصيغة المناسبة
        local_status = await convert_api_status(api_status)
        
        # تحويل remains إلى عدد صحيح
        try:
            remains_int = int(remains)
        except (ValueError, TypeError):
            remains_int = 0
        
        # تحديث الكمية المتبقية، والتي ستقوم تلقائيًا بتحديث الحالة إذا كانت 0
        updated = await update_order_remains_simple(order_id, remains_int)
        
        if updated:
            # تحديث الحالة إذا لم تكن متوافقة مع حالة الكمية المتبقية
            current_status = order.get("status", "").lower()
            
            if current_status != local_status:
                await update_order_status(order_id, local_status)
                logger.info(f"تم تحديث حالة الطلب {order_id} من {current_status} إلى {local_status}")
            
            logger.info(f"تم تحديث الطلب {order_id} بنجاح: الحالة={local_status}, المتبقي={remains_int}")
            return True
        else:
            logger.warning(f"فشل تحديث الطلب {order_id}")
            return False
    except Exception as e:
        logger.error(f"خطأ غير متوقع في تحديث الطلب: {e}")
        return False

async def update_orders_batch(orders: List[Dict[str, Any]]) -> int:
    """
    تحديث مجموعة من الطلبات دفعة واحدة باستخدام طلب API متعدد
    
    Args:
        orders: قائمة بالطلبات المراد تحديثها
        
    Returns:
        int: عدد الطلبات التي تم تحديثها بنجاح
    """
    try:
        if not orders:
            return 0
        
        # استخراج معرفات الطلبات (تخطي الطلبات المحلية)
        order_ids = [
            str(order.get("order_id")) 
            for order in orders 
            if order.get("order_id") and not str(order.get("order_id")).startswith("LOCAL-")
        ]
        
        if not order_ids:
            return 0
        
        # طلب حالة الطلبات من API
        api_response = await check_multiple_orders(order_ids)
        
        if "error" in api_response:
            logger.warning(f"خطأ في تحديث دفعة الطلبات: {api_response['error']}")
            return 0
        
        # عداد الطلبات التي تم تحديثها بنجاح
        success_count = 0
        
        # معالجة كل طلب في الاستجابة
        for order_id, status_data in api_response.items():
            if "error" in status_data:
                logger.warning(f"خطأ في تحديث الطلب {order_id}: {status_data['error']}")
                continue
            
            # استخراج البيانات من استجابة API
            api_status = status_data.get("status", "")
            remains = status_data.get("remains", "0")
            
            # تحويل البيانات إلى الصيغة المناسبة
            local_status = await convert_api_status(api_status)
            
            # تحويل remains إلى عدد صحيح
            try:
                remains_int = int(remains)
            except (ValueError, TypeError):
                remains_int = 0
            
            # تحديث الطلب في قاعدة البيانات
            updated = await update_order_remains_simple(order_id, remains_int)
            
            if updated:
                # تأكد من تحديث الحالة (لاحظ أن update_order_remains_simple تقوم بذلك جزئيًا)
                await update_order_status(order_id, local_status)
                logger.info(f"تم تحديث الطلب {order_id}: الحالة={local_status}, المتبقي={remains_int}")
                success_count += 1
        
        return success_count
    except Exception as e:
        logger.error(f"خطأ في تحديث دفعة الطلبات: {e}")
        return 0

async def update_all_orders() -> int:
    """
    تحديث جميع الطلبات النشطة
    
    Returns:
        int: عدد الطلبات التي تم تحديثها بنجاح
    """
    try:
        # الحصول على الطلبات النشطة
        active_orders = await get_active_orders()
        
        if not active_orders:
            logger.info("لا توجد طلبات نشطة للتحديث")
            return 0
        
        # عداد إجمالي الطلبات المحدثة
        total_updated = 0
        
        # تقسيم الطلبات إلى دفعات لتحسين الأداء
        for i in range(0, len(active_orders), BATCH_SIZE):
            batch = active_orders[i:i+BATCH_SIZE]
            
            # تحديث الدفعة باستخدام طلب API متعدد
            updated_count = await update_orders_batch(batch)
            total_updated += updated_count
            
            # انتظار قصير بين الدفعات لتجنب إرهاق API
            if i + BATCH_SIZE < len(active_orders):
                await asyncio.sleep(1)
        
        logger.info(f"تم تحديث {total_updated} طلب من أصل {len(active_orders)}")
        return total_updated
    except Exception as e:
        logger.error(f"خطأ في تحديث جميع الطلبات: {e}")
        return 0

async def start_order_status_updater():
    """
    بدء مهمة تحديث حالة الطلبات بشكل دوري
    """
    logger.info("تم بدء مهمة تحديث حالة الطلبات الدورية")
    
    while True:
        try:
            # تسجيل وقت بدء التحديث
            start_time = time.time()
            
            # تنفيذ التحديث
            await update_all_orders()
            
            # حساب المدة المستغرقة
            elapsed_time = time.time() - start_time
            logger.info(f"اكتمل تحديث الطلبات في {elapsed_time:.2f} ثانية")
            
            # الانتظار حتى الدورة التالية
            await asyncio.sleep(UPDATE_INTERVAL)
        except asyncio.CancelledError:
            # المهمة تم إلغاؤها
            logger.info("تم إلغاء مهمة تحديث حالة الطلبات")
            break
        except Exception as e:
            # خطأ غير متوقع، سجل وحاول مرة أخرى بعد الفاصل
            logger.error(f"خطأ غير متوقع في مهمة تحديث الطلبات: {e}")
            await asyncio.sleep(UPDATE_INTERVAL)

async def schedule_order_status_updater(app):
    """
    جدولة مهمة تحديث حالة الطلبات الدورية
    
    Args:
        app: تطبيق البوت (للتسجيل في الخلفية)
    """
    try:
        # إنشاء المهمة وتخزينها في تطبيق البوت لتجنب إنهائها
        app["order_status_task"] = asyncio.create_task(start_order_status_updater())
        logger.info("تمت جدولة مهمة تحديث حالة الطلبات بنجاح")
    except Exception as e:
        logger.error(f"فشل جدولة مهمة تحديث حالة الطلبات: {e}")