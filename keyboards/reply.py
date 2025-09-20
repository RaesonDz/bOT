"""
ملف لإنشاء لوحات المفاتيح النصية
"""

from typing import List, Tuple
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Add this import if config.py is not already imported.
import config

# تعريف الأزرار المشتركة
_BACK_BUTTON = KeyboardButton(text="🔙 العودة للقائمة الرئيسية")
_DEPOSIT_BUTTON = KeyboardButton(text="💰 إيداع رصيد")
_MY_ORDERS_BUTTON = KeyboardButton(text="📋 طلباتي السابقة")
_NEW_ORDER_BUTTON = KeyboardButton(text="📦 طلب جديد")
_BALANCE_BUTTON = KeyboardButton(text="💵 رصيدي")
_DEPOSITS_HISTORY_BUTTON = KeyboardButton(text="📊 تاريخ الإيداعات")
_CONTACT_BUTTON = KeyboardButton(text="📞 اتصل بنا")
_REFRESH_BUTTON = KeyboardButton(text="🔄 تحديث")

# أزرار المشرف
_ADMIN_PANEL_BUTTON = KeyboardButton(text="👑 لوحة المشرف")
_STATS_BUTTON = KeyboardButton(text="📊 إحصائيات")
_DEPOSIT_REQUESTS_BUTTON = KeyboardButton(text="📦 طلبات الإيداع")
_ALL_DEPOSITS_BUTTON = KeyboardButton(text="📥 جميع الإيداعات")
_USERS_BUTTON = KeyboardButton(text="👥 المستخدمين")
_RANKS_BUTTON = KeyboardButton(text="🏆 إدارة الرتب")
_RECENT_ORDERS_BUTTON = KeyboardButton(text="🛒 آخر الطلبات")
_MANAGE_ORDERS_BUTTON = KeyboardButton(text="🛒 إدارة الطلبات")
_MANAGE_USERS_BUTTON = KeyboardButton(text="👥 إدارة المستخدمين")
_SEND_NOTIFICATION_BUTTON = KeyboardButton(text="📢 إرسال إشعار")
_QUICK_STATS_BUTTON = KeyboardButton(text="📊 إحصائيات سريعة")
_PENDING_DEPOSITS_BUTTON = KeyboardButton(text="📦 طلبات الإيداع المعلقة")
_SYSTEM_MONITOR_BUTTON = KeyboardButton(text="🔍 مراقبة النظام")
_SALES_REPORT_BUTTON = KeyboardButton(text="📈 تقارير البيع")
_BOT_SETTINGS_BUTTON = KeyboardButton(text="🛠️ إعدادات البوت")
_USER_MENU_BUTTON = KeyboardButton(text="📱 قائمة المستخدم")
_MAIN_MENU_BUTTON = KeyboardButton(text="🔙 العودة للقائمة الرئيسية")
_ADMIN_MAIN_BUTTON = KeyboardButton(text="👑 لوحة المشرف")
_SYSTEM_UPDATE_BUTTON = KeyboardButton(text="🔄 تحديث النظام")



# لوحة المفاتيح الرئيسية للمستخدم
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """الحصول على لوحة المفاتيح الرئيسية للمستخدم"""
    keyboard = [
        [KeyboardButton(text="🔄 طلب جديد"), KeyboardButton(text="🔍 طلباتي السابقة")],
        [KeyboardButton(text="💰 رصيدي"), KeyboardButton(text="💸 إيداع رصيد")],
        [KeyboardButton(text="📜 تاريخ الإيداعات"), KeyboardButton(text="📞 اتصل بنا")],
        [KeyboardButton(text="🔄 تحديث")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# لوحة مفاتيح العودة
def get_back_keyboard() -> ReplyKeyboardMarkup:
    """إنشاء لوحة مفاتيح العودة"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[_BACK_BUTTON]],
        resize_keyboard=True
    )
    return keyboard

# لوحة مفاتيح تأكيد الإيداع
def get_confirm_deposit_keyboard() -> ReplyKeyboardMarkup:
    """إنشاء لوحة مفاتيح تأكيد الإيداع"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ تأكيد")],
            [KeyboardButton(text="❌ إلغاء")],
            [_BACK_BUTTON]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

# لوحة مفاتيح تأكيد الطلب
def get_confirm_order_keyboard() -> ReplyKeyboardMarkup:
    """إنشاء لوحة مفاتيح تأكيد الطلب"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ تأكيد الطلب")],
            [KeyboardButton(text="❌ إلغاء الطلب")],
            [_BACK_BUTTON]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

# لوحة مفاتيح طرق الدفع
def get_payment_methods_keyboard() -> ReplyKeyboardMarkup:
    """لوحة مفاتيح طرق الدفع"""
    keyboard = []

    # إضافة طرق الدفع المتاحة
    for method_key, method_data in config.PAYMENT_METHODS.items():
        keyboard.append([KeyboardButton(text=method_data["name"])])

    # إضافة زر العودة
    keyboard.append([KeyboardButton(text="🔙 العودة")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# لوحة مفاتيح الاتصال
def get_contact_keyboard() -> ReplyKeyboardMarkup:
    """إنشاء لوحة مفاتيح الاتصال"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 طلب مساعدة")],
            [KeyboardButton(text="❓ الأسئلة الشائعة")],
            [_BACK_BUTTON]
        ],
        resize_keyboard=True
    )
    return keyboard

# لوحة المفاتيح الرئيسية للمشرف (القائمة المختصرة)
def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """الحصول على لوحة المفاتيح الرئيسية للمشرف"""
    keyboard = [
        [KeyboardButton(text="🔄 طلب جديد"), KeyboardButton(text="🔍 طلباتي السابقة")],
        [KeyboardButton(text="💰 رصيدي"), KeyboardButton(text="💸 إيداع رصيد")],
        [KeyboardButton(text="📜 تاريخ الإيداعات"), KeyboardButton(text="📞 اتصل بنا")],
        [KeyboardButton(text="👑 لوحة المشرف"), KeyboardButton(text="🔄 تحديث")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# لوحة المفاتيح الكاملة للمشرف
def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """
    الحصول على لوحة مفاتيح المشرف مع إشعارات بسيطة لطلبات الإيداع المعلقة

    تم تغيير الدالة من async إلى عادية (sync) لسهولة استخدامها في أي سياق
    تستخدم رمز التنبيه 🔴 بدلاً من العد التفصيلي لتبسيط العملية
    """
    try:
        import asyncio
        from database.deposit import get_pending_deposits
        from utils.common import create_animated_badge
        
        # محاولة الكشف عن طلبات الإيداع المعلقة (بشكل غير متزامن)
        try:
            # إنشاء حلقة أحداث مؤقتة (إذا لم تكن موجودة)
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # استدعاء الدالة المتزامنة والحصول على النتائج
            pending_deposits, _ = loop.run_until_complete(get_pending_deposits())
            
            # تحديد ما إذا كانت هناك طلبات معلقة
            has_pending_deposits = len(pending_deposits) > 0
            
            # تحديد رمز الإيداعات (إضافة نقطة حمراء إذا كانت هناك طلبات معلقة)
            deposits_emoji = "💰 🔴" if has_pending_deposits else "💰"
            
        except Exception as e:
            # في حالة حدوث خطأ، استخدم نص بسيط
            import logging
            logger = logging.getLogger("smm_bot")
            logger.error(f"خطأ في التحقق من طلبات الإيداع المعلقة: {e}")
            deposits_emoji = "💰"
            
        # إنشاء لوحة المفاتيح مع الرمز المناسب
        keyboard = [
            [KeyboardButton(text="📊 إحصائيات"), KeyboardButton(text="👥 المستخدمين")],
            [KeyboardButton(text=f"{deposits_emoji} طلبات الإيداع"), KeyboardButton(text="📢 إرسال إشعار")],
            [KeyboardButton(text="📦 الطلبات"), KeyboardButton(text="🔄 مزامنة الخدمات")],
            [KeyboardButton(text="🏆 إدارة الرتب"), KeyboardButton(text="⚙️ الإعدادات")],
            [KeyboardButton(text="🔙 العودة للوضع العادي")]
        ]
        
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
        
    except Exception as e:
        # في حالة حدوث خطأ جذري، استخدم لوحة المفاتيح الافتراضية
        import logging
        logger = logging.getLogger("smm_bot")
        logger.error(f"خطأ جذري في إنشاء لوحة مفاتيح المشرف: {e}")
        
        # لوحة المفاتيح الافتراضية البسيطة
        keyboard = [
            [KeyboardButton(text="📊 إحصائيات"), KeyboardButton(text="👥 المستخدمين")],
            [KeyboardButton(text="💰 طلبات الإيداع"), KeyboardButton(text="📢 إرسال إشعار")],
            [KeyboardButton(text="📦 الطلبات"), KeyboardButton(text="🔄 مزامنة الخدمات")],
            [KeyboardButton(text="🏆 إدارة الرتب"), KeyboardButton(text="⚙️ الإعدادات")],
            [KeyboardButton(text="🔙 العودة للوضع العادي")]
        ]
        
        return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# لوحة مفاتيح إدارة طلبات الإيداع
def get_deposit_management_keyboard() -> ReplyKeyboardMarkup:
    """لوحة مفاتيح إدارة الإيداعات"""
    keyboard = [
        [KeyboardButton(text="📥 الطلبات المعلقة")],
        [KeyboardButton(text="✅ الطلبات الموافق عليها")],
        [KeyboardButton(text="❌ الطلبات المرفوضة")],
        [KeyboardButton(text="🔙 العودة")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# لوحة مفاتيح إدارة المستخدمين
def get_user_management_keyboard() -> ReplyKeyboardMarkup:
    """لوحة مفاتيح إدارة المستخدمين"""
    keyboard = [
        [KeyboardButton(text="➕ إضافة مستخدم")],
        [KeyboardButton(text="🔍 البحث عن مستخدم")],
        [KeyboardButton(text="🔙 العودة")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# لوحة مفاتيح إدارة الطلبات
def get_order_management_keyboard() -> ReplyKeyboardMarkup:
    """إنشاء لوحة مفاتيح إدارة الطلبات"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 الكل"), KeyboardButton(text="🕒 معلق")],
            [KeyboardButton(text="⏳ قيد المعالجة"), KeyboardButton(text="✅ مكتمل")],
            [KeyboardButton(text="❌ ملغي"), KeyboardButton(text="⚠️ فشل")],
            [KeyboardButton(text="التالي ▶️"), KeyboardButton(text="◀️ السابق")],
            [KeyboardButton(text="🔙 العودة")]
        ],
        resize_keyboard=True
    )
    return keyboard

# لوحة مفاتيح الإلغاء
def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """لوحة مفاتيح الإلغاء"""
    keyboard = [[KeyboardButton(text="❌ إلغاء")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)

# لوحة مفاتيح التأكيد
def get_confirmation_keyboard() -> ReplyKeyboardMarkup:
    """لوحة مفاتيح التأكيد (نعم/لا)"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ نعم"), KeyboardButton(text="❌ لا")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

# لوحة مفاتيح العودة للمشرف
def get_admin_back_keyboard() -> ReplyKeyboardMarkup:
    """إنشاء لوحة مفاتيح العودة للمشرف"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 العودة")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_categories_keyboard(categories: List[Tuple[int, str]]) -> ReplyKeyboardMarkup:
    """
    إنشاء لوحة مفاتيح للفئات
    Args:
        categories: قائمة الفئات
    Returns:
        لوحة المفاتيح
    """
    keyboard = []
    # وضع كل فئة في صف منفرد لكامل عرض الشاشة
    for category in categories:
        keyboard.append([KeyboardButton(text=category[1])])

    # إضافة زر العودة
    keyboard.append([KeyboardButton(text="🔙 العودة")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_services_keyboard(services: List[dict]) -> ReplyKeyboardMarkup:
    """
    إنشاء لوحة مفاتيح للخدمات
    Args:
        services: قائمة الخدمات
    Returns:
        لوحة المفاتيح
    """
    keyboard = []
    for service in services:
        service_id = service.get("service", "غير محدد")
        name = service.get("name", "غير محدد")
        price = service.get("rate", "غير محدد")

        # تحديد نوع التسعير وتنسيق السعر
        try:
            max_order = int(service.get("max", 0)) if isinstance(service.get("max"), str) else service.get("max", 0)
            price_format = "للباقة" if max_order == 1 else "لكل 1000"
        except (ValueError, TypeError):
            price_format = "لكل 1000"

        # تنسيق نص الزر مع نوع التسعير
        button_text = f"{service_id}. {name} ({price}$ {price_format})"

        keyboard.append([KeyboardButton(text=button_text)])

    # إضافة أزرار الإلغاء والعودة
    keyboard.append([
        KeyboardButton(text="🔙 العودة"),
        KeyboardButton(text="❌ إلغاء")
    ])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_deposit_cancel_keyboard() -> ReplyKeyboardMarkup:
    """لوحة مفاتيح إلغاء الإيداع"""
    keyboard = [
        [KeyboardButton(text="⚠️ لم أقم بالإيداع بعد")],
        [KeyboardButton(text="❌ إلغاء عملية الإيداع")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_user_search_keyboard() -> ReplyKeyboardMarkup:
    """لوحة مفاتيح البحث عن مستخدم"""
    keyboard = [
        [KeyboardButton(text="🆔 البحث بالمعرف")],
        [KeyboardButton(text="👤 البحث بالاسم")],
        [KeyboardButton(text="🔙 العودة")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_orders_detail_keyboard(current_page: int, total_pages: int) -> ReplyKeyboardMarkup:
    """
    لوحة مفاتيح طلبات المستخدم مع أزرار التنقل بين الصفحات
    Args:
        current_page: الصفحة الحالية
        total_pages: العدد الإجمالي للصفحات
    Returns:
        لوحة المفاتيح
    """
    keyboard = []
    nav_buttons = []

    # أزرار التنقل
    # زر الصفحة السابقة
    if current_page > 1:
        nav_buttons.append(KeyboardButton(text="⬅️ السابق"))

    # زر العودة
    nav_buttons.append(KeyboardButton(text="🔙 العودة"))

    # زر الصفحة التالية
    if current_page < total_pages:
        nav_buttons.append(KeyboardButton(text="➡️ التالي"))

    keyboard.append(nav_buttons)
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_pagination_keyboard(current_page: int, total_pages: int) -> ReplyKeyboardMarkup:
    """
    لوحة مفاتيح التنقل بين الصفحات
    Args:
        current_page: الصفحة الحالية
        total_pages: العدد الإجمالي للصفحات
    Returns:
        لوحة المفاتيح
    """
    keyboard = []
    buttons = []

    # زر الصفحة السابقة
    if current_page > 1:
        buttons.append(KeyboardButton(text="⬅️ السابق"))

    # زر العودة
    buttons.append(KeyboardButton(text="🔙 العودة"))

    # زر الصفحة التالية
    if current_page < total_pages:
        buttons.append(KeyboardButton(text="➡️ التالي"))

    keyboard.append(buttons)

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)