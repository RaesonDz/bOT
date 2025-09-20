"""
واجهة التعامل مع API الخارجية

هذا الملف يحتوي على دوال للتعامل مع API الخارجية للخدمات، مثل إنشاء الطلبات
والتحقق من حالة الطلبات والحصول على قائمة الخدمات المتاحة.
"""

import os
import logging
import aiohttp
import json
from typing import Dict, List, Any, Optional
import asyncio
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

# إعداد المسجل
logger = logging.getLogger("smm_bot")

# الحصول على بيانات API من المتغيرات البيئية
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL", "https://garren.store/api/v2")

# جلسة HTTP عامة للاستخدام في جميع الطلبات
_session = None

async def init_api_session():
    """
    تهيئة جلسة API للاتصال بالخدمة الخارجية
    
    Returns:
        aiohttp.ClientSession: جلسة الاتصال
    """
    global _session
    if _session is None:
        _session = aiohttp.ClientSession()
        logger.info("تم تهيئة جلسة API")
    return _session

async def close_api_session():
    """إغلاق جلسة API وتحرير الموارد"""
    global _session
    if _session:
        await _session.close()
        _session = None
        logger.info("تم إغلاق جلسة API")

async def make_api_request(action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    إنشاء طلب إلى API الخارجية وإرجاع النتيجة

    Args:
        action: نوع الإجراء المطلوب (balance, services, add, status, etc.)
        params: معلمات إضافية للطلب (اختياري)

    Returns:
        Dict[str, Any]: استجابة API كقاموس
        في حالة الخطأ، يحتوي القاموس على مفتاح "error" مع وصف الخطأ
    """
    global _session
    
    # التأكد من وجود مفتاح API
    if not API_KEY:
        logger.error("مفتاح API غير موجود")
        return {"error": "مفتاح API غير موجود. يرجى توفير مفتاح API في ملف .env"}
    
    # التأكد من تهيئة الجلسة
    if _session is None:
        await init_api_session()

    # تكوين معلمات الطلب الأساسية
    payload = {
        "key": API_KEY,
        "action": action
    }
    
    # إضافة المعلمات الإضافية إذا تم توفيرها
    if params is not None:
        payload.update(params)
    
    # تسجيل معلومات الطلب للتصحيح (مع إخفاء مفتاح API للأمان)
    debug_payload = payload.copy()
    if "key" in debug_payload:
        debug_payload["key"] = "****"
    logger.debug(f"إرسال طلب API ({action}): {debug_payload}")
    
    try:
        # التأكد من وجود جلسة صالحة
        if not _session or _session.closed:
            logger.warning("الجلسة مغلقة أو غير موجودة، إعادة تهيئتها")
            await init_api_session()
            
        # إرسال الطلب
        if _session:
            try:
                async with _session.post(API_URL, data=payload, timeout=30) as response:
                    # تسجيل معلومات الاستجابة الأولية
                    logger.debug(f"استجابة API {action}: {response.status}")
                    
                    # معالجة استجابة الخادم حسب رمز الحالة
                    if response.status == 200:
                        try:
                            # تحليل الاستجابة كـ JSON
                            try:
                                result = await response.json()
                                return result
                            except Exception:
                                # في حالة الفشل، قراءة النص أولاً ثم محاولة تحليله كـ JSON يدويًا
                                response_text = await response.text()
                                try:
                                    # محاولة تحليل النص يدويًا
                                    result = json.loads(response_text)
                                    return result
                                except json.JSONDecodeError as e:
                                    # فشل التحليل اليدوي أيضًا
                                    logger.error(f"خطأ في تحليل استجابة API ({action}): {e} - {response_text}")
                                    return {"error": f"خطأ في تنسيق استجابة API: {e}"}
                        except json.JSONDecodeError as e:
                            # تعامل مع استجابة ليست بتنسيق JSON صالح
                            response_text = await response.text()
                            logger.error(f"خطأ في تحليل استجابة API ({action}): {e} - {response_text}")
                            return {"error": f"خطأ في تنسيق استجابة API: {e}"}
                    elif response.status == 404:
                        # غالبًا تشير إلى مشكلة في عنوان API أو الإجراء
                        logger.error(f"خطأ في طلب API ({action}): {response.status}")
                        logger.error(f"العنوان غير موجود: {action}")
                        return {"error": f"عنوان API غير صحيح: {API_URL} أو الإجراء غير مدعوم: {action}"}
                    else:
                        # أخطاء أخرى في استجابة الخادم
                        response_text = await response.text()
                        logger.error(f"خطأ في استجابة API ({action}): {response.status} - {response_text}")
                        return {"error": f"خطأ في استجابة API: {response.status} - {response_text}"}
            except asyncio.TimeoutError:
                logger.error(f"انتهت مهلة الاتصال بـ API ({action})")
                return {"error": "انتهت مهلة الاتصال بـ API"}
        else:
            logger.error("فشل الاتصال: لم يتم تهيئة الجلسة بشكل صحيح")
            return {"error": "فشل الاتصال: لم يتم تهيئة الجلسة بشكل صحيح"}
    except aiohttp.ClientError as e:
        logger.error(f"خطأ في الاتصال بـ API ({action}): {e}")
        return {"error": f"خطأ في الاتصال: {e}"}
    except Exception as e:
        logger.error(f"خطأ غير متوقع أثناء الاتصال بـ API ({action}): {e}")
        return {"error": f"خطأ غير متوقع: {e}"}

async def test_api_connection() -> bool:
    """
    اختبار الاتصال بـ API عن طريق طلب رصيد الحساب

    Returns:
        bool: True إذا كان الاتصال ناجحًا، False إذا فشل
    """
    try:
        # اختبار الاتصال باستخدام طلب رصيد الحساب
        result = await make_api_request("balance")
        
        # التحقق من وجود أخطاء في الاستجابة
        if "error" in result:
            logger.error(f"فشل اختبار الاتصال بـ API: {result['error']}")
            return False
        
        logger.info("اختبار الاتصال بـ API ناجح")
        return True
    except Exception as e:
        logger.error(f"فشل اختبار الاتصال بـ API: {e}")
        return False

async def get_balance() -> Dict:
    """
    الحصول على رصيد الحساب من API

    Returns:
        Dict: قاموس يحتوي على معلومات الرصيد
        عادة يحتوي على مفتاحي "balance" و"currency"
    """
    try:
        result = await make_api_request("balance")
        
        if "error" in result:
            logger.error(f"فشل الحصول على رصيد الحساب: {result['error']}")
            return result
        
        logger.info(f"تم الحصول على رصيد الحساب بنجاح: {result}")
        return result
    except Exception as e:
        logger.error(f"فشل الحصول على رصيد الحساب: {e}")
        return {"error": f"فشل الحصول على رصيد الحساب: {e}"}

async def get_services() -> List[Dict]:
    """
    الحصول على قائمة الخدمات المتاحة من API

    Returns:
        List[Dict]: قائمة بالخدمات المتاحة
        كل خدمة تحتوي على معلومات مثل service (الرقم)، name (الاسم)، وغيرها
    """
    try:
        result = await make_api_request("services")
        
        if isinstance(result, dict) and "error" in result:
            logger.error(f"فشل الحصول على قائمة الخدمات: {result['error']}")
            return []
        
        # التحقق من نوع الاستجابة والتعامل معها بشكل مناسب
        if isinstance(result, list):
            logger.info(f"تم استرجاع {len(result)} خدمة من API")
            return result
        elif isinstance(result, dict):
            # تحويل القاموس إلى قائمة إذا لزم الأمر
            logger.warning("تم استلام قاموس بدلاً من قائمة، محاولة التحويل")
            services_list = [result] if "error" not in result else []
            return services_list
        else:
            logger.error("نوع بيانات غير متوقع من API")
            return []
    except Exception as e:
        logger.error(f"فشل الحصول على قائمة الخدمات: {e}")
        return []

async def create_order(service_id: int, link: str, quantity: int) -> Dict:
    """
    إنشاء طلب جديد عبر API

    Args:
        service_id: معرف الخدمة
        link: الرابط المستهدف
        quantity: الكمية المطلوبة

    Returns:
        Dict: نتيجة العملية كقاموس
        في حالة النجاح يحتوي على مفتاح "order" مع رقم الطلب
    """
    try:
        params = {
            "service": service_id,
            "link": link,
            "quantity": quantity
        }
        
        result = await make_api_request("add", params)
        
        if "error" in result:
            logger.error(f"فشل إنشاء الطلب: {result['error']}")
            return result
        
        logger.info(f"تم إنشاء الطلب بنجاح: {result}")
        return result
    except Exception as e:
        logger.error(f"فشل إنشاء الطلب: {e}")
        return {"error": f"فشل إنشاء الطلب: {e}"}

async def check_order_status(order_id: str) -> Dict:
    """
    التحقق من حالة الطلب عبر API

    Args:
        order_id: معرف الطلب

    Returns:
        Dict: معلومات حالة الطلب كقاموس
        يحتوي على مفاتيح مثل status (الحالة) و remains (المتبقي)
    """
    try:
        # التأكد من أن معرف الطلب نص وليس رقمًا
        order_id_str = str(order_id).strip()
        
        # التحقق من صحة معرف الطلب
        if not order_id_str.isdigit():
            logger.warning(f"معرف الطلب غير صالح: {order_id_str}")
            return {
                "error": "معرف الطلب غير صالح",
                "status": "pending",
                "remains": "0"
            }
            
        # التهيئة الصحيحة للمعلمات حسب توثيق API
        params = {
            "order": order_id_str
        }
        
        # إرسال طلب API
        logger.debug(f"إرسال طلب التحقق من حالة الطلب: {order_id_str}")
        result = await make_api_request("status", params)
        
        # فحص الاستجابة للأخطاء
        if isinstance(result, dict) and "error" in result:
            error_msg = result.get("error", "خطأ غير معروف")
            logger.error(f"فشل التحقق من حالة الطلب {order_id_str}: {error_msg}")
            
            # استجابة احتياطية في حالة الخطأ
            return {
                "error": error_msg,
                "status": "pending",
                "remains": "0"
            }
            
        # التحقق من وجود المعلومات الأساسية في الاستجابة
        if not isinstance(result, dict):
            logger.warning(f"استجابة API غير متوقعة لطلب {order_id_str}: {result}")
            return {
                "error": "استجابة API غير متوقعة",
                "status": "pending",
                "remains": "0"
            }
            
        # تسجيل نجاح العملية
        logger.info(f"تم التحقق من حالة الطلب {order_id_str} بنجاح: {result}")
        
        # تأكد من وجود الحقول الأساسية وإضافتها إذا كانت غير موجودة
        if "status" not in result:
            result["status"] = "pending"
        if "remains" not in result:
            result["remains"] = "0"
            
        return result
    except Exception as e:
        logger.error(f"خطأ غير متوقع في التحقق من حالة الطلب {order_id}: {e}")
        return {
            "error": f"خطأ غير متوقع: {e}",
            "status": "pending",
            "remains": "0"
        }

async def check_multiple_orders(order_ids: List[str]) -> Dict:
    """
    التحقق من حالة مجموعة من الطلبات في طلب واحد

    Args:
        order_ids: قائمة بمعرفات الطلبات (يمكن التحقق من حتى 100 طلب)

    Returns:
        Dict: معلومات حالة الطلبات كقاموس مفاتيحه هي معرفات الطلبات
    """
    try:
        # تحضير معلمة الطلبات بفصلها بفواصل كما هو مطلوب في API
        orders_param = ",".join(str(order_id) for order_id in order_ids)
        params = {
            "orders": orders_param
        }
        
        result = await make_api_request("status", params)
        
        if "error" in result:
            logger.error(f"فشل التحقق من حالة الطلبات: {result['error']}")
            return result
        
        logger.info(f"تم التحقق من حالة {len(order_ids)} طلب بنجاح")
        return result
    except Exception as e:
        logger.error(f"فشل التحقق من حالة الطلبات: {e}")
        return {"error": f"فشل التحقق من حالة الطلبات: {e}"}

def organize_services_by_category(services: List[Dict]) -> Dict[str, List[Dict]]:
    """
    تنظيم الخدمات حسب الفئة لتسهيل عرضها وإدارتها

    Args:
        services: قائمة بالخدمات من API

    Returns:
        Dict[str, List[Dict]]: قاموس بالخدمات مقسمة حسب الفئة
        حيث المفاتيح هي أسماء الفئات والقيم هي قوائم الخدمات في كل فئة
    """
    categories: Dict[str, List[Dict]] = {}
    
    try:
        for service in services:
            # استخراج اسم الفئة والتأكد من وجوده
            category_name = service.get("category", "أخرى")
            
            # إنشاء الفئة إذا لم تكن موجودة
            if category_name not in categories:
                categories[category_name] = []
            
            # إضافة الخدمة إلى الفئة المناسبة
            categories[category_name].append(service)
        
        logger.info(f"تم تنظيم الخدمات في {len(categories)} فئة")
    except Exception as e:
        logger.error(f"خطأ أثناء تنظيم الخدمات: {e}")
    
    return categories

async def add_order(service_id: int, link: str, quantity: int) -> Dict:
    """
    إضافة طلب جديد (مرادف لـ create_order)

    Args:
        service_id: معرف الخدمة
        link: الرابط المستهدف
        quantity: الكمية المطلوبة

    Returns:
        Dict: نتيجة العملية كقاموس
    """
    return await create_order(service_id, link, quantity)

async def get_user_orders(user_id: int) -> List[Dict]:
    """
    الحصول على طلبات المستخدم من قاعدة البيانات المحلية
    
    هذه الدالة تتطلب التكامل مع قاعدة البيانات المحلية وليس مع API الخارجية

    Args:
        user_id: معرف المستخدم

    Returns:
        List[Dict]: قائمة بطلبات المستخدم
    """
    from database.core import get_user_orders as db_get_user_orders
    
    try:
        # استدعاء دالة قاعدة البيانات للحصول على طلبات المستخدم
        orders, total = await db_get_user_orders(user_id)
        logger.info(f"تم استرجاع {len(orders)} طلب للمستخدم {user_id}")
        return orders
    except Exception as e:
        logger.error(f"فشل استرجاع طلبات المستخدم {user_id}: {e}")
        return []