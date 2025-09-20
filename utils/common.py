"""
وحدة الوظائف المساعدة المشتركة
"""

import logging
import logging.config
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import re

def setup_logging(logger_name, log_level=logging.INFO):
    """إعداد التسجيل للتطبيق"""
    # إنشاء دليل السجلات إذا لم يكن موجودًا
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # تكوين ملف السجل مع التاريخ
    log_file = os.path.join(logs_dir, f"{logger_name}_{datetime.now().strftime('%Y-%m-%d')}.log")

    # تكوين التسجيل
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "filename": log_file,
                "mode": "a",
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["console", "file"],
                "level": "DEBUG",
                "propagate": False
            },
            logger_name: {
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False
            },
            "aiogram": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            }
        }
    }

    # تطبيق التكوين
    logging.config.dictConfig(logging_config)

    # إنشاء وإعادة المسجل
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    return logger

def format_money(amount: float) -> str:
    """تنسيق المبلغ المالي"""
    if amount is None:
        return "0.00"
    
    # التعامل مع القيمة كسلسلة نصية إذا كانت كذلك
    try:
        if isinstance(amount, str):
            # محاولة تحويل السلسلة النصية إلى رقم عشري إذا أمكن
            amount = float(amount)
        
        # تحقق من حجم الرقم لاختيار التنسيق المناسب
        if amount < 0.01:
            # استخدام 4 أرقام عشرية للقيم الصغيرة جدا
            return f"{float(amount):.4f}"
        elif amount < 0.1:
            # استخدام 3 أرقام عشرية للقيم الصغيرة
            return f"{float(amount):.3f}"
        else:
            # استخدام رقمين عشريين للقيم العادية
            return f"{float(amount):.2f}"
    except (ValueError, TypeError):
        # إذا لم يمكن التحويل، نعيد القيمة كما هي
        return str(amount)

def format_amount_with_currency(amount: float, payment_method: str = "USD") -> str:
    """
    تنسيق المبلغ المالي مع عرض العملة المناسبة
    
    Args:
        amount: المبلغ المالي
        payment_method: طريقة الدفع (USD أو BARIDIMOB أو غيرها)
        
    Returns:
        النص المنسق للمبلغ مع العملة
    """
    if amount is None:
        return "$0.00"
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return f"${amount}"
    
    # عرض المبلغ حسب طريقة الدفع
    if payment_method == "BARIDIMOB":
        # المبلغ بالدينار الجزائري
        amount_dzd = amount
        # تحويل المبلغ بالدينار إلى دولار (1$ = 260 دينار)
        amount_usd = amount_dzd / 260
        
        # تنسيق المبلغ بالدينار الجزائري والدولار
        dzd_formatted = format_money(amount_dzd)
        usd_formatted = format_money(amount_usd)
        
        return f"{dzd_formatted} دينار\n💵 ما يعادل: ${usd_formatted}"
    else:
        # بقية طرق الدفع تستخدم الدولار
        return f"${format_money(amount)}"

def validate_number(value: str) -> tuple:
    """التحقق من صحة القيمة الرقمية
    
    Args:
        value: القيمة المراد التحقق منها
        
    Returns:
        tuple: (is_valid: bool, amount: float, error_msg: str)
    """
    try:
        if not value or not value.strip():
            return False, 0, "يرجى إدخال قيمة رقمية صالحة."
        
        # إزالة أي أحرف غير رقمية باستثناء النقطة العشرية
        clean_value = re.sub(r'[^\d.]', '', value)
        amount = float(clean_value)
        
        if amount <= 0:
            return False, 0, "يجب أن يكون المبلغ أكبر من صفر."
            
        return True, amount, ""
    except (ValueError, TypeError):
        return False, 0, "القيمة المدخلة ليست رقمًا صالحًا. يرجى إدخال رقم فقط."

def validate_integer(value: str) -> Optional[int]:
    """التحقق من صحة القيمة العددية الصحيحة"""
    try:
        if not value or not value.strip():
            return None
        # إزالة أي أحرف غير رقمية
        clean_value = re.sub(r'[^\d]', '', value)
        return int(clean_value)
    except (ValueError, TypeError):
        return None

def validate_url(url: str) -> bool:
    """التحقق من صحة عنوان URL"""
    if not url or not url.strip():
        return False

    # نمط التحقق البسيط من URL
    url_pattern = re.compile(
        r'^(https?://)?(www\.)?'  # بروتوكول http:// أو https:// (اختياري)
        r'([a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+)'  # اسم النطاق
        r'(:\d+)?(/[-a-zA-Z0-9%_.~#+]*)*'  # المنفذ والمسار
        r'(\?[a-zA-Z0-9%&=]*)?'  # معلمات الاستعلام
        r'(#[-a-zA-Z0-9]*)?$'  # الشظية
    )

    return bool(url_pattern.match(url))

def format_user_info(user_data: Dict[str, Any]) -> str:
    """تنسيق معلومات المستخدم"""
    user_id = user_data.get("user_id", "غير محدد")
    username = user_data.get("username", "غير محدد")
    full_name = user_data.get("full_name", "غير محدد")
    balance = user_data.get("balance", 0)
    created_at = user_data.get("created_at", "غير محدد")
    last_activity = user_data.get("last_activity", "غير محدد")

    from database.ranks import get_rank_emoji, get_rank_name
    rank_id = user_data.get("rank_id", 5)
    rank_emoji = get_rank_emoji(rank_id)
    rank_name = get_rank_name(rank_id)

    user_text = (
        f"👤 <b>معلومات المستخدم:</b>\n\n"
        f"🆔 <b>المعرف:</b> {user_id}\n"
        f"👤 <b>اسم المستخدم:</b> @{username}\n"
        f"📝 <b>الاسم الكامل:</b> {full_name}\n"
        f"💰 <b>الرصيد:</b> ${format_money(balance)}\n"
        f"🏆 <b>الرتبة:</b> {rank_emoji} {rank_name}\n"
        f"📅 <b>تاريخ التسجيل:</b> {created_at}\n"
        f"⏱️ <b>آخر نشاط:</b> {last_activity}\n"
    )

    return user_text

def format_deposit_info(deposit_data: Optional[Dict[str, Any]]) -> str:
    """تنسيق معلومات طلب الإيداع"""
    if deposit_data is None:
        return "⚠️ لا توجد بيانات للطلب"
        
    deposit_id = deposit_data.get("id", "غير محدد")
    user_id = deposit_data.get("user_id", "غير محدد")
    username = deposit_data.get("username", "غير محدد")
    amount = deposit_data.get("amount", 0)
    payment_method = deposit_data.get("payment_method", "غير محدد")
    status = deposit_data.get("status", "pending")
    created_at = deposit_data.get("created_at", "غير محدد")
    receipt_url = deposit_data.get("receipt_url", "لا يوجد")
    receipt_info = deposit_data.get("receipt_info", "")

    # تنسيق الحالة
    status_emoji = "🕒"  # معلق
    status_text = "معلق"
    if status == "approved":
        status_emoji = "✅"  # تمت الموافقة
        status_text = "تمت الموافقة"
    elif status == "rejected":
        status_emoji = "❌"  # تم الرفض
        status_text = "تم الرفض"
    elif status == "refunded":
        status_emoji = "♻️"  # تم استرداد المبلغ
        status_text = "تم استرداد المبلغ"

    # استخدام الدالة الجديدة لتنسيق المبلغ مع العملة
    amount_display = format_amount_with_currency(amount, payment_method)

    deposit_text = (
        f"💰 <b>معلومات طلب الإيداع:</b>\n\n"
        f"🔢 <b>رقم الطلب:</b> {deposit_id}\n"
        f"👤 <b>المستخدم:</b> {user_id} (@{username})\n"
        f"💵 <b>المبلغ:</b> {amount_display}\n"
        f"💳 <b>طريقة الدفع:</b> {payment_method}\n"
        f"📊 <b>الحالة:</b> {status_emoji} {status_text}\n"
        f"📅 <b>تاريخ الطلب:</b> {created_at}\n"
    )

    # إضافة معلومات الإيصال إذا كانت متوفرة
    if receipt_url and receipt_url != "لا يوجد":
        deposit_text += f"🧾 <b>إيصال الدفع:</b> {receipt_url}\n"
    
    # إضافة معلومات إضافية إذا كانت متوفرة
    if receipt_info:
        deposit_text += f"📝 <b>معلومات إضافية:</b> {receipt_info}\n"

    return deposit_text

def truncate_text(text: str, max_length: int = 500) -> str:
    """اقتصاص النص إلى الطول الأقصى مع إضافة "..." إذا كان أطول"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

async def cleanup_resources():
    """تنظيف الموارد عند إغلاق البوت"""
    logger = logging.getLogger("smm_bot")
    logger.info("بدء تنظيف الموارد...")

    try:
        # تنظيف جلسات API
        from services.api import close_api_session
        await close_api_session()
        logger.info("تم إغلاق جلسة API بنجاح")
    except Exception as e:
        logger.error(f"خطأ في إغلاق جلسة API: {e}")

    try:
        # إلغاء المهام المعلقة
        import asyncio
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            logger.info(f"إلغاء {len(tasks)} مهمة معلقة")
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("اكتمل تنظيف الموارد")
    except Exception as e:
        logger.error(f"خطأ في إلغاء المهام المعلقة: {e}")

# تنسيق المبالغ المالية

# التحقق من صحة الأرقام

# إنشاء الشارات المتحركة للإشعارات
def create_animated_badge(count: int, emoji: str = "🔔") -> str:
    """
    إنشاء رمز إشعارات للاستخدام في واجهة المستخدم
    
    Args:
        count: عدد الإشعارات
        emoji: رمز تعبيري للاستخدام (افتراضيًا 🔔)
        
    Returns:
        الرمز التعبيري المناسب بناءً على وجود إشعارات أو عدمه
    """
    if count <= 0:
        return emoji  # إذا لم تكن هناك إشعارات، أعد الرمز التعبيري العادي
    
    # استخدام الرمز الأحمر للإشارة إلى وجود إشعارات جديدة
    return "🔴"

# تنسيق معلومات الخدمة
def format_service_info(service: Dict[str, Any]) -> str:
    """
    تنسيق معلومات الخدمة للعرض
    Args:
        service: معلومات الخدمة
    Returns:
        نص منسق لمعلومات الخدمة
    """
    service_id = service.get("service", "غير محدد")
    name = service.get("name", "غير محدد")
    rate = service.get("rate", 0)
    min_order = service.get("min", 0)
    max_order = service.get("max", 0)

    # تحديد نوع التسعير وتنسيق السعر
    if max_order == 1:
        # إذا كان الحد الأقصى يساوي 1، فهذه باقة
        price_format = "للباقة"
    else:
        # غير ذلك، استخدم التنسيق العادي
        price_format = "لكل 1000" if service.get("price_per_1k", True) else "للوحدة"

    return (
        f"<b>🆔 رقم الخدمة:</b> {service_id}\n"
        f"<b>📋 الخدمة:</b> {name}\n"
        f"<b>💲 السعر:</b> ${format_money(rate)} {price_format}\n"
        f"<b>⬇️ الحد الأدنى:</b> {min_order}\n"
        f"<b>⬆️ الحد الأقصى:</b> {max_order}"
    )

# تنسيق معلومات الطلب
def format_order_info(order: Dict[str, Any]) -> str:
    """
    تنسيق معلومات الطلب للعرض
    Args:
        order: معلومات الطلب
    Returns:
        نص منسق لمعلومات الطلب
    """
    order_id = order.get("order_id", "غير محدد")
    service_name = order.get("service_name", "غير محدد")
    link = order.get("link", "غير محدد")
    quantity = order.get("quantity", 0)
    amount = order.get("amount", 0)
    status = order.get("status", "قيد الانتظار")
    created_at = order.get("created_at", "غير محدد")

    # ترجمة حالة الطلب
    status_map = {
        "Pending": "قيد الانتظار",
        "In Progress": "قيد التنفيذ",
        "Completed": "مكتمل",
        "Canceled": "ملغي",
        "Partial": "مكتمل جزئيًا",
        "Processing": "قيد المعالجة",
        "Failed": "فشل"
    }

    translated_status = status_map.get(status, status)

    return (
        f"<b>🆔 رقم الطلب:</b> {order_id}\n"
        f"<b>📋 الخدمة:</b> {service_name}\n"
        f"<b>🔗 الرابط:</b> {link}\n"
        f"<b>🔢 الكمية:</b> {quantity}\n"
        f"<b>💰 المبلغ:</b> ${format_money(amount)}\n"
        f"<b>🔄 الحالة:</b> {translated_status}\n"
        f"<b>📆 تاريخ الإنشاء:</b> {created_at}"
    )


# تنسيق معلومات المستخدم


# مزامنة رصيد المشرف من API
async def sync_admin_balance_from_api():
    """
    مزامنة رصيد المشرف من API
    """
    logger = logging.getLogger("smm_bot")
    try:
        # استدعاء دالة الحصول على الرصيد من API
        from services.api import get_balance
        balance_data = await get_balance()

        if balance_data:
            # تسجيل الرصيد المسترجع
            balance_value = balance_data.get("balance", 0)
            logger.info(f"تم استرجاع رصيد المشرف من API: {balance_value}")
            return balance_value
        else:
            logger.warning("لم يتم الحصول على بيانات الرصيد من API")
            return None
    except Exception as e:
        logger.error(f"خطأ في مزامنة رصيد المشرف: {e}")
        return None


def escape_html(text: str) -> str:
    """
    هروب أحرف HTML الخاصة
    Args:
        text: النص المراد معالجته
    Returns:
        النص بعد معالجة أحرف HTML الخاصة
    """
    if not text:
        return ""

    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")