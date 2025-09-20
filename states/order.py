"""
حالات البوت المختلفة
"""

from aiogram.fsm.state import StatesGroup, State

class OrderState(StatesGroup):
    """مجموعة حالات إنشاء الطلب"""
    selecting_category = State()  # اختيار الفئة
    selecting_service = State()   # اختيار الخدمة
    entering_link = State()       # إدخال الرابط
    entering_quantity = State()   # إدخال الكمية
    confirming_order = State()    # تأكيد الطلب

class DepositState(StatesGroup):
    """مجموعة حالات طلب الإيداع"""
    selecting_method = State()  # اختيار طريقة الإيداع
    selecting_payment_method = State()  # اختيار وسيلة الدفع (مرادف لـ selecting_method)
    entering_amount = State()   # إدخال المبلغ
    uploading_receipt = State() # رفع إيصال الدفع
    sending_receipt = State()   # إرسال الإيصال (مرادف لـ uploading_receipt)
    confirming_receipt = State() # تأكيد إرسال الإيصال والمسؤولية
    confirming_deposit = State() # تأكيد طلب الإيداع

class UserState(StatesGroup):
    """مجموعة حالات إعدادات المستخدم"""
    changing_language = State()  # تغيير اللغة
    entering_feedback = State()  # إدخال ملاحظات وتقييم
    viewing_orders = State()     # عرض الطلبات
    viewing_deposits = State()   # عرض الإيداعات

class AdminState(StatesGroup):
    """مجموعة حالات لوحة التحكم"""
    viewing_users = State()       # عرض المستخدمين
    managing_users = State()      # إدارة المستخدمين (مرادف لـ viewing_users)
    viewing_user_details = State() # عرض تفاصيل مستخدم
    editing_user = State()        # تعديل مستخدم
    entering_add_balance_amount = State() # إدخال مبلغ لإضافة رصيد
    entering_subtract_balance_amount = State() # إدخال مبلغ لطرح رصيد
    viewing_orders = State()      # عرض الطلبات
    managing_orders = State()     # إدارة الطلبات (مرادف لـ viewing_orders)
    viewing_deposits = State()    # عرض الإيداعات
    managing_deposits = State()   # إدارة الإيداعات (مرادف لـ viewing_deposits)
    managing_all_deposits = State() # إدارة جميع الإيداعات
    approving_deposit = State()   # الموافقة على إيداع
    confirming_refund = State()   # تأكيد استرداد الإيداع
    entering_reject_reason = State() # إدخال سبب رفض طلب الإيداع
    sending_broadcast = State()   # إرسال بث جماعي
    sending_notification = State() # إرسال إشعار
    confirming_notification = State() # تأكيد إرسال الإشعار
    editing_rank_name = State()   # تعديل اسم الرتبة
    editing_rank_features = State() # تعديل مميزات الرتبة
    syncing_services = State()    # مزامنة الخدمات
    
    # إدارة التسعير
    adding_pricing_rule = State() # إضافة قاعدة تسعير
    editing_pricing_rule = State() # تعديل قاعدة تسعير
    
    # إدارة الخدمات والفئات
    managing_services = State()   # إدارة الخدمات
    adding_category = State()     # إضافة فئة
    editing_service = State()     # تعديل خدمة