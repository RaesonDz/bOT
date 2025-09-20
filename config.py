
"""
ملف الإعدادات الرئيسية للبوت
"""

import os
import logging
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

# إنشاء مسجل
logger = logging.getLogger("smm_bot")

# معلومات البوت
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.warning("تحذير: لم يتم تعيين BOT_TOKEN. يرجى إضافته في ملف .env")

# معلومات البوت
BOT_NAME = os.getenv("BOT_NAME", "Garren Services Store")
BOT_USERNAME = os.getenv("BOT_USERNAME", "SmmDz_bot")
BOT_DESCRIPTION = os.getenv("BOT_DESCRIPTION", "خدمات السوشيال ميديا بأقل الأسعار")

# إعداد حسابات المشرفين
admin_ids_str = os.getenv("ADMIN_IDS", "5464520756")
ADMIN_IDS = []
try:
    if admin_ids_str:
        ADMIN_IDS = [int(id_str.strip()) for id_str in admin_ids_str.split(",") if id_str.strip()]
    # التأكد من إضافة المشرف الرئيسي دائمًا
    if 5464520756 not in ADMIN_IDS:
        ADMIN_IDS.append(5464520756)
    logger.info(f"قائمة المشرفين المعتمدين: {ADMIN_IDS}")
except Exception as e:
    logger.error(f"خطأ في تكوين المشرفين: {e}")
    # في حالة الفشل، نستخدم المشرف الرئيسي فقط
    ADMIN_IDS = [5464520756]

# معلومات الاتصال بالمشرف
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@Garren_store")

# إعدادات API
API_URL = os.getenv("API_URL", "https://garren.store/api/v2")
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    logger.warning("تحذير: لم يتم تعيين API_KEY. بعض الوظائف قد لا تعمل")

# إعدادات قاعدة البيانات
DB_NAME = os.getenv("DATABASE_PATH", "database.db")
DATABASE_PATH = DB_NAME  # للتوافق مع الكود القديم

# إعدادات الطلبات
MIN_ORDER = int(os.getenv("MIN_ORDER", "10"))  # الحد الأدنى للطلب الافتراضي

# معلومات الاتصال
CONTACT_INFO = {
    "email": os.getenv("CONTACT_EMAIL", "support@garren.store"),
    "telegram": os.getenv("CONTACT_TELEGRAM", "@Garren_store"),
    "website": os.getenv("CONTACT_WEBSITE", "https://garren.store")
}

# نص الاتصال بنا
CONTACT_US_TEXT = """
📞 <b>اتصل بنا:</b>

إذا كان لديك أي استفسار أو مشكلة، يمكنك التواصل معنا عبر:

🔹 <b>البريد الإلكتروني:</b> {email}
🔹 <b>تيليجرام:</b> {admin_username}
🔹 <b>الموقع:</b> {website}

نحن نعمل على مدار الساعة للرد على استفساراتك في أسرع وقت ممكن.
""".format(
    email=CONTACT_INFO["email"],
    admin_username=ADMIN_USERNAME,
    website=CONTACT_INFO["website"]
)

# طرق الدفع
PAYMENT_METHODS = {
    "USDT": {
        "name": "💰 USDT TRC-20",
        "wallet": os.getenv("USDT_WALLET", "TTLNTfwvWGgrrWT5AA8WatnCEhk4tLvzQc"),
        "network": "TRC-20",
        "min_deposit": 5  # الحد الأدنى 5 دولار
    },
    "BARIDIMOB": {
        "name": "💳 بريدي موب (DZD)",
        "account": os.getenv("BARIDIMOB_ACCOUNT", "00799999002283570811"),
        "holder_name": os.getenv("BARIDIMOB_HOLDER", "Garren Store"),
        "min_deposit": 1300  # الحد الأدنى 1300 دينار جزائري
    }
}
