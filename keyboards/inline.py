"""
لوحات المفاتيح الإنلاين المستخدمة في البوت
"""

from typing import List, Tuple, Optional, Union, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.ranks import get_rank_emoji, get_all_ranks
import config

def get_main_menu() -> InlineKeyboardMarkup:
    """لوحة المفاتيح الرئيسية الإنلاين"""
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 طلب جديد", callback_data="new_order"),
            InlineKeyboardButton(text="🔍 طلباتي السابقة", callback_data="my_orders")
        ],
        [
            InlineKeyboardButton(text="💰 رصيدي", callback_data="my_balance"),
            InlineKeyboardButton(text="💸 إيداع رصيد", callback_data="deposit")
        ],
        [
            InlineKeyboardButton(text="📞 اتصل بنا", callback_data="contact_us"),
            InlineKeyboardButton(text="❓ مساعدة", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_menu() -> InlineKeyboardMarkup:
    """إنشاء قائمة المشرف الإنلاين"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 المستخدمون", callback_data="admin_users")],
            [InlineKeyboardButton(text="💰 طلبات الإيداع", callback_data="admin_deposits")],
            [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="admin_statistics")],
            [InlineKeyboardButton(text="📢 إرسال إشعار", callback_data="admin_send_notification")]
        ]
    )
    return keyboard

def get_admin_deposits_menu():
    """إنشاء قائمة إدارة الإيداعات"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏳ طلبات الإيداع المعلقة", callback_data="admin_deposits")],
            [InlineKeyboardButton(text="📜 سجل جميع الإيداعات", callback_data="admin_all_deposits")],
            [InlineKeyboardButton(text="🔍 البحث عن إيداع", callback_data="admin_search_deposit")],
            [InlineKeyboardButton(text="🔙 العودة", callback_data="admin_menu")]
        ]
    )
    return keyboard

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """لوحة مفاتيح لوحة تحكم المشرف"""
    keyboard = [
        [
            InlineKeyboardButton(text="📦 طلبات الإيداع", callback_data="admin_deposits"),
            InlineKeyboardButton(text="👥 المستخدمين", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="🛒 إدارة الطلبات", callback_data="admin_orders"),
            InlineKeyboardButton(text="📊 الإحصائيات", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="📣 إرسال إشعار", callback_data="admin_notification"),
            InlineKeyboardButton(text="🏆 إدارة الرتب", callback_data="manage_ranks")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)



def get_skip_keyboard() -> InlineKeyboardMarkup:
    """لوحة مفاتيح التخطي بأزرار إنلاين"""
    keyboard = [
        [
            InlineKeyboardButton(text="⏭️ تخطي", callback_data="skip_action"),
            InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_action")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """لوحة مفاتيح التأكيد بأزرار إنلاين"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ نعم", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ لا", callback_data="confirm_no")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_balance_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """لوحة مفاتيح إدارة رصيد المستخدم"""
    keyboard = [
        [
            InlineKeyboardButton(text="💰 إضافة رصيد", callback_data=f"add_balance_{user_id}"),
            InlineKeyboardButton(text="💸 خصم رصيد", callback_data=f"subtract_balance_{user_id}")
        ],
        [
            InlineKeyboardButton(text="🏆 تغيير الرتبة", callback_data=f"assign_rank_{user_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_users")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_user_management_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """لوحة مفاتيح إدارة مستخدم معين"""
    keyboard = [
        [
            InlineKeyboardButton(text="💲 إضافة رصيد", callback_data=f"add_balance_{user_id}"),
            InlineKeyboardButton(text="🔻 خصم رصيد", callback_data=f"subtract_balance_{user_id}")
        ],
        [
            InlineKeyboardButton(text="🏆 تعيين رتبة", callback_data=f"assign_rank_{user_id}"),
            InlineKeyboardButton(text="🚫 حظر/إلغاء حظر", callback_data=f"toggle_ban_{user_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 العودة لقائمة المستخدمين", callback_data="manage_users")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_methods_keyboard() -> InlineKeyboardMarkup:
    """لوحة مفاتيح طرق الدفع"""
    keyboard = []

    # إضافة أزرار لكل طريقة دفع
    for method_key, method_info in sorted(config.PAYMENT_METHODS.items()):
        keyboard.append([
            InlineKeyboardButton(
                text=method_info['name'],
                callback_data=f"payment_method_{method_key}"
            )
        ])

    # زر العودة للقائمة الرئيسية
    keyboard.append([
        InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_user_orders_keyboard(page: int = 1, total_pages: int = 1) -> InlineKeyboardMarkup:
    """لوحة مفاتيح طلبات المستخدم"""
    keyboard = []

    # أزرار التنقل بين الصفحات
    if total_pages > 1:
        navigation = []

        if page > 1:
            navigation.append(
                InlineKeyboardButton(
                    text="◀️ السابق",
                    callback_data=f"orders_page_{page-1}"
                )
            )

        navigation.append(
            InlineKeyboardButton(
                text=f"📄 {page}/{total_pages}",
                callback_data="orders_page_info"
            )
        )

        if page < total_pages:
            navigation.append(
                InlineKeyboardButton(
                    text="التالي ▶️",
                    callback_data=f"orders_page_{page+1}"
                )
            )

        keyboard.append(navigation)

    # زر العودة للقائمة الرئيسية
    keyboard.append([
        InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="back_to_main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_deposit_confirmation_keyboard(deposit_id: int) -> InlineKeyboardMarkup:
    """لوحة مفاتيح تأكيد الإيداع"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ تأكيد الإيداع", callback_data=f"confirm_deposit_{deposit_id}"),
            InlineKeyboardButton(text="❌ إلغاء", callback_data=f"cancel_deposit_{deposit_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_deposit_actions(deposit_id: Union[str, int], status: str = "pending") -> InlineKeyboardMarkup:
    """
    أزرار إجراءات طلب الإيداع للمشرف
    
    Args:
        deposit_id: معرف طلب الإيداع
        status: حالة طلب الإيداع (pending/approved/rejected/refunded)
    """
    keyboard = []
    
    # الأزرار تعتمد على الحالة الحالية للطلب
    if status == "pending":
        # إذا كان الطلب معلقًا، أظهر أزرار الموافقة والرفض
        keyboard.append([
            InlineKeyboardButton(
                text="✅ موافقة", 
                callback_data=f"approve_deposit_{deposit_id}"
            ),
            InlineKeyboardButton(
                text="❌ رفض", 
                callback_data=f"reject_deposit_{deposit_id}"
            )
        ])
    elif status == "approved":
        # إذا تمت الموافقة، أظهر زر الاسترداد
        keyboard.append([
            InlineKeyboardButton(
                text="♻️ استرداد المبلغ", 
                callback_data=f"refund_deposit_{deposit_id}"
            )
        ])
    
    # أضف دائمًا زر التفاصيل
    keyboard.append([
        InlineKeyboardButton(
            text="🔍 عرض إيصال الدفع", 
            callback_data=f"view_receipt_{deposit_id}"
        ),
        InlineKeyboardButton(
            text="👤 معلومات المستخدم", 
            callback_data=f"view_user_deposit_{deposit_id}"
        )
    ])
    
    # زر العودة يختلف حسب الحالة
    if status == "pending":
        keyboard.append([InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_deposits")])
    elif status == "approved":
        keyboard.append([InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_deposits")])
    elif status == "rejected":
        keyboard.append([InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_deposits")])
    else:
        keyboard.append([InlineKeyboardButton(text="🔙 العودة", callback_data="admin_all_deposits")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_confirm_order_keyboard() -> InlineKeyboardMarkup:
    """لوحة مفاتيح تأكيد الطلب"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ تأكيد الطلب", callback_data="confirm_order"),
            InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_order")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_ranks_management_keyboard() -> InlineKeyboardMarkup:
    """لوحة مفاتيح إدارة الرتب"""
    ranks = await get_all_ranks()
    keyboard = []

    # إضافة أزرار للرتب
    for rank in ranks:
        rank_id = rank.get("id", 5)
        rank_name = rank.get("name", "برونزي")
        emoji = get_rank_emoji(rank_id)

        keyboard.append([
            InlineKeyboardButton(
                text=f"{emoji} {rank_name}", 
                callback_data=f"rank_info_{rank_id}"
            )
        ])

    # زر تحديث جميع الرتب
    keyboard.append([
        InlineKeyboardButton(
            text="🔄 تحديث رتب المستخدمين", 
            callback_data="update_all_ranks"
        )
    ])

    # زر العودة
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 العودة", 
            callback_data="admin_menu"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_rank_actions_keyboard(rank_id: int) -> InlineKeyboardMarkup:
    """لوحة مفاتيح إجراءات الرتبة"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ تعديل الاسم", 
                callback_data=f"edit_rank_name_{rank_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔧 تعديل الميزات", 
                callback_data=f"edit_rank_features_{rank_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="💰 تعديل الحد الأدنى للرصيد", 
                callback_data=f"edit_rank_min_{rank_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 العودة لقائمة الرتب", 
                callback_data="manage_ranks"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_user_rank_selection_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """لوحة مفاتيح اختيار رتبة للمستخدم"""
    # الحصول على قائمة الرتب
    ranks = await get_all_ranks()

    # ترتيب الرتب حسب المعرف تصاعديا (1، 2، 3...)
    ranks_sorted = sorted(ranks, key=lambda r: r.get("id", 999))

    buttons = []
    for rank in ranks_sorted:
        rank_id = rank.get("id", 5)
        rank_name = rank.get("name", "برونزي")
        emoji = get_rank_emoji(rank_id)
        buttons.append([
            InlineKeyboardButton(text=f"{emoji} {rank_name}", callback_data=f"set_user_rank_{user_id}_{rank_id}")
        ])

    buttons.append([
        InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_users")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_deposit_confirmation_keyboard(deposit_id: int) -> InlineKeyboardMarkup:
    """لوحة مفاتيح تأكيد الإيداع"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ تأكيد الإيداع", callback_data=f"confirm_deposit_{deposit_id}"),
            InlineKeyboardButton(text="❌ إلغاء", callback_data=f"cancel_deposit_{deposit_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_upload_receipt_keyboard() -> InlineKeyboardMarkup:
    """لوحة مفاتيح رفع إيصال الدفع"""
    keyboard = [
        [
            InlineKeyboardButton(text="📤 رفع إيصال الدفع", callback_data="upload_receipt")
        ],
        [
            InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel_deposit")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_button(callback_data: str = "back_to_main") -> InlineKeyboardMarkup:
    """زر العودة"""
    keyboard = [
        [
            InlineKeyboardButton(text="🔙 العودة", callback_data=callback_data)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """زر الإلغاء"""
    keyboard = [
        [
            InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_pagination_keyboard(current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    """لوحة مفاتيح التنقل بين الصفحات"""
    keyboard = []

    # أزرار التنقل
    navigation = []

    if current_page > 1:
        navigation.append(InlineKeyboardButton(text="◀️ السابق", callback_data=f"{prefix}_prev"))

    navigation.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data=f"{prefix}_page"))

    if current_page < total_pages:
        navigation.append(InlineKeyboardButton(text="التالي ▶️", callback_data=f"{prefix}_next"))

    if navigation:
        keyboard.append(navigation)

    # زر العودة
    keyboard.append([InlineKeyboardButton(text="🔙 العودة", callback_data=f"{prefix}_back")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_deposits_management_keyboard(deposits: List[Dict[str, Any]], page: int = 1) -> InlineKeyboardMarkup:
    """
    إنشاء لوحة مفاتيح إدارة طلبات الإيداع
    
    Args:
        deposits: قائمة طلبات الإيداع
        page: رقم الصفحة الحالية
    
    Returns:
        لوحة مفاتيح الإنلاين للإدارة
    """
    from utils.common import create_animated_badge
    
    keyboard = []
    
    # أزرار التصفية
    filter_buttons = []
    
    # إضافة عدد الطلبات المعلقة كشارة متحركة
    pending_count = sum(1 for d in deposits if d.get("status") == "pending")
    pending_badge = create_animated_badge(pending_count, "⏳")
    filter_buttons.append(InlineKeyboardButton(
        text=f"{pending_badge} المعلقة", 
        callback_data="filter_pending_deposits"
    ))
    
    # إضافة أزرار التصفية الأخرى
    filter_buttons.append(InlineKeyboardButton(
        text="✅ المقبولة", 
        callback_data="filter_approved_deposits"
    ))
    
    keyboard.append(filter_buttons)
    
    # أزرار لعرض تفاصيل الإيداعات
    for i in range(min(5, len(deposits))):
        deposit = deposits[i]
        deposit_id = deposit.get("id", 0)
        user_id = deposit.get("user_id", "غير محدد")
        username = deposit.get("username", "غير محدد")
        
        if username and not username.startswith("@"):
            username = f"@{username}"
            
        keyboard.append([
            InlineKeyboardButton(
                text=f"🆔 {deposit_id} | 👤 {username}",
                callback_data=f"deposit_details_{deposit_id}"
            )
        ])
    
    # أزرار التنقل بين الصفحات
    navigation = []
    total_pages = max(1, (len(deposits) + 4) // 5)  # 5 items per page
    
    if page > 1:
        navigation.append(InlineKeyboardButton(
            text="◀️ السابق",
            callback_data="deposits_prev_page"
        ))
    
    navigation.append(InlineKeyboardButton(
        text=f"📄 {page}/{total_pages}",
        callback_data="deposits_current_page"
    ))
    
    if page < total_pages:
        navigation.append(InlineKeyboardButton(
            text="التالي ▶️",
            callback_data="deposits_next_page"
        ))
    
    if navigation:
        keyboard.append(navigation)
    
    # زر العودة
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 العودة للقائمة الرئيسية",
            callback_data="admin_menu"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_ranks_management_keyboard() -> InlineKeyboardMarkup:
    """لوحة مفاتيح إدارة الرتب"""
    from database.ranks import get_all_ranks

    ranks = await get_all_ranks()
    keyboard = []

    # إضافة زر لكل رتبة
    for rank in ranks:
        rank_id = rank.get("id", 0)
        name = rank.get("name", "غير معروف")
        keyboard.append([InlineKeyboardButton(text=f"🏆 {name}", callback_data=f"rank_info_{rank_id}")])

    # أزرار إضافية
    keyboard.append([
        InlineKeyboardButton(text="🔁 تحديث رتب المستخدمين", callback_data="update_all_ranks")
    ])

    # زر العودة
    keyboard.append([
        InlineKeyboardButton(text="🔙 العودة", callback_data="admin_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_rank_actions_keyboard(rank_id: int) -> InlineKeyboardMarkup:
    """لوحة مفاتيح إجراءات الرتبة"""
    keyboard = [
        [
            InlineKeyboardButton(text="✏️ تعديل الاسم", callback_data=f"edit_rank_name_{rank_id}"),
            InlineKeyboardButton(text="🔧 تعديل الميزات", callback_data=f"edit_rank_features_{rank_id}")
        ],
        [
            InlineKeyboardButton(text="💰 تعديل الحد الأدنى", callback_data=f"edit_rank_min_{rank_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 العودة", callback_data="manage_ranks")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def get_user_rank_selection_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """لوحة مفاتيح اختيار الرتبة للمستخدم"""
    from database.ranks import get_all_ranks

    ranks = await get_all_ranks()
    keyboard = []

    # إضافة زر لكل رتبة
    for rank in ranks:
        rank_id = rank.get("id", 0)
        name = rank.get("name", "غير معروف")
        keyboard.append([
            InlineKeyboardButton(
                text=f"🏆 {name}", 
                callback_data=f"set_user_rank_{user_id}_{rank_id}"
            )
        ])

    # زر العودة
    keyboard.append([
        InlineKeyboardButton(text="🔙 العودة", callback_data="back_to_users")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)