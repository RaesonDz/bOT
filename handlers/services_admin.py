"""
معالجات إدارة الخدمات والفئات للمشرف
"""

import logging
from typing import Dict, Any, List

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

import config
from database.services import (
    get_categories, get_services, sync_services_from_api,
    update_category_visibility, update_service_visibility,
    create_category
)
from database.pricing import calculate_service_price
from database.ranks import get_all_ranks
from services.api import get_services as get_api_services
from states.order import AdminState
from utils.common import format_money

# إنشاء مسجل
logger = logging.getLogger("smm_bot")

# إنشاء موجه
router = Router(name="services_admin")

@router.message(F.text == "🛍️ إدارة الخدمات")
async def services_management(message: Message, state: FSMContext):
    """معالج إدارة الخدمات الرئيسي"""
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    try:
        # الحصول على إحصائيات الخدمات
        categories = await get_categories(include_inactive=True)
        services = await get_services(include_inactive=True)
        
        active_categories = [c for c in categories if c['is_active']]
        active_services = [s for s in services if s['is_active']]
        
        stats_text = f"""
🛍️ <b>لوحة إدارة الخدمات</b>

📊 <b>الإحصائيات:</b>
🔹 <b>إجمالي الفئات:</b> {len(categories)} ({len(active_categories)} نشطة)
🔹 <b>إجمالي الخدمات:</b> {len(services)} ({len(active_services)} نشطة)

📋 <b>العمليات المتاحة:</b>
"""
        
        # إنشاء لوحة المفاتيح
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 مزامنة من API", callback_data="services_sync_api"),
                InlineKeyboardButton(text="📂 إدارة الفئات", callback_data="services_manage_categories")
            ],
            [
                InlineKeyboardButton(text="🎯 إدارة الخدمات", callback_data="services_manage_services"),
                InlineKeyboardButton(text="👁‍🗨 إعدادات الظهور", callback_data="services_visibility")
            ],
            [
                InlineKeyboardButton(text="💰 معاينة الأسعار", callback_data="services_price_preview"),
                InlineKeyboardButton(text="📊 إحصائيات تفصيلية", callback_data="services_detailed_stats")
            ],
            [
                InlineKeyboardButton(text="🔙 العودة", callback_data="admin_main")
            ]
        ])
        
        await message.answer(
            stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"خطأ في إدارة الخدمات: {e}")
        await message.answer("⚠️ حدث خطأ أثناء تحميل معلومات الخدمات.")

@router.callback_query(F.data == "services_sync_api")
async def sync_services_from_api_handler(callback: CallbackQuery, state: FSMContext):
    """مزامنة الخدمات من API الخارجي"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    try:
        # إرسال رسالة تحميل
        loading_msg = await callback.message.edit_text(
            "🔄 <b>جاري مزامنة الخدمات من API...</b>\n\n"
            "⏳ يرجى الانتظار، قد يستغرق هذا بعض الوقت.",
            parse_mode=ParseMode.HTML
        )
        
        # الحصول على الخدمات من API
        api_services = await get_api_services()
        
        if not api_services:
            await callback.message.edit_text(
                "❌ <b>فشل في الحصول على الخدمات من API</b>\n\n"
                "تأكد من صحة إعدادات API والاتصال بالإنترنت.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 العودة", callback_data="services_management")]
                ])
            )
            return
        
        # مزامنة الخدمات
        sync_stats = await sync_services_from_api(api_services)
        
        # عرض نتائج المزامنة
        result_text = f"""
✅ <b>اكتملت مزامنة الخدمات بنجاح!</b>

📊 <b>نتائج المزامنة:</b>
🆕 <b>خدمات جديدة:</b> {sync_stats['created']}
🔄 <b>خدمات محدثة:</b> {sync_stats['updated']}
❌ <b>أخطاء:</b> {sync_stats['errors']}
📦 <b>إجمالي الخدمات:</b> {len(api_services)}

💰 <b>الخطوة التالية:</b>
يمكنك الآن تطبيق قواعد التسعير على الخدمات الجديدة من قسم "إدارة التسعير".
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 إدارة التسعير", callback_data="pricing_management"),
                InlineKeyboardButton(text="🎯 إدارة الخدمات", callback_data="services_manage_services")
            ],
            [
                InlineKeyboardButton(text="🔙 العودة", callback_data="services_management")
            ]
        ])
        
        await callback.message.edit_text(
            result_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        logger.info(f"تمت مزامنة الخدمات: {sync_stats}")
        
    except Exception as e:
        logger.error(f"خطأ في مزامنة الخدمات: {e}")
        await callback.message.edit_text(
            "❌ <b>حدث خطأ أثناء مزامنة الخدمات</b>\n\n"
            f"تفاصيل الخطأ: {str(e)[:200]}...",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 العودة", callback_data="services_management")]
            ])
        )

@router.callback_query(F.data == "services_manage_categories")
async def manage_categories(callback: CallbackQuery, state: FSMContext):
    """إدارة الفئات"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    try:
        categories = await get_categories(include_inactive=True)
        
        if not categories:
            await callback.message.edit_text(
                "📂 <b>إدارة الفئات</b>\n\n"
                "❌ لا توجد فئات حالياً.\n"
                "قم بمزامنة الخدمات من API أولاً لإنشاء الفئات تلقائياً.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 مزامنة من API", callback_data="services_sync_api")],
                    [InlineKeyboardButton(text="🔙 العودة", callback_data="services_management")]
                ])
            )
            return
        
        # عرض الفئات مع التصفح
        page = 0
        categories_per_page = 4
        await show_categories_page(callback, state, categories, page, categories_per_page)
        
    except Exception as e:
        logger.error(f"خطأ في إدارة الفئات: {e}")
        await callback.answer("❌ حدث خطأ أثناء تحميل الفئات.")

async def show_categories_page(callback, state, categories, page, per_page):
    """عرض صفحة من الفئات"""
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_categories = categories[start_idx:end_idx]
    
    text = f"📂 <b>إدارة الفئات</b>\n\n"
    text += f"📄 الصفحة {page + 1} من {(len(categories) - 1) // per_page + 1}\n\n"
    
    keyboard_rows = []
    
    for category in page_categories:
        # رمز الحالة
        status_emoji = "🟢" if category['is_active'] else "🔴"
        visibility_emoji = "👁" if category['visibility_min_rank'] <= 3 else "🔒"
        
        # إضافة معلومات الفئة
        text += f"<b>{status_emoji} {category['name']}</b>\n"
        text += f"┣ 🆔 المعرف: {category['id']}\n"
        text += f"┣ {visibility_emoji} ظهور للرتب: {category['visibility_min_rank']}+\n"
        text += f"┗ 📅 تاريخ الإنشاء: {category['created_at'][:10]}\n\n"
        
        # إضافة أزرار التحكم
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"{'🔴 إخفاء' if category['is_active'] else '🟢 إظهار'} ({category['id']})", 
                callback_data=f"cat_toggle_{category['id']}"
            ),
            InlineKeyboardButton(
                text=f"👁 رتب ({category['id']})", 
                callback_data=f"cat_visibility_{category['id']}"
            )
        ])
    
    # أزرار التنقل
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ السابق", callback_data=f"categories_page_{page-1}"))
    if end_idx < len(categories):
        nav_row.append(InlineKeyboardButton(text="➡️ التالي", callback_data=f"categories_page_{page+1}"))
    
    if nav_row:
        keyboard_rows.append(nav_row)
    
    keyboard_rows.append([InlineKeyboardButton(text="🔙 العودة", callback_data="services_management")])
    
    await state.update_data(categories_list=categories, current_categories_page=page, categories_per_page=per_page)
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )

@router.callback_query(F.data.startswith("cat_toggle_"))
async def toggle_category_visibility(callback: CallbackQuery, state: FSMContext):
    """تبديل حالة إظهار/إخفاء الفئة"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    category_id = int(callback.data.split("_")[-1])
    
    # الحصول على حالة الفئة الحالية
    categories = await get_categories(include_inactive=True)
    category = next((c for c in categories if c['id'] == category_id), None)
    
    if not category:
        await callback.answer("❌ الفئة غير موجودة.")
        return
    
    # تبديل الحالة
    new_status = not category['is_active']
    success = await update_category_visibility(category_id, new_status)
    
    if success:
        status_text = "تم إظهار الفئة" if new_status else "تم إخفاء الفئة"
        await callback.answer(f"✅ {status_text} بنجاح.")
    else:
        await callback.answer("❌ فشل في تحديث حالة الفئة.")
    
    # إعادة عرض الصفحة
    await manage_categories(callback, state)

@router.callback_query(F.data == "services_price_preview")
async def services_price_preview(callback: CallbackQuery, state: FSMContext):
    """معاينة أسعار الخدمات مع التسعير المطبق"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    # عرض خيارات الرتب لمعاينة الأسعار
    ranks = await get_all_ranks()
    
    keyboard_rows = []
    
    for rank in ranks:
        from database.ranks import get_rank_emoji
        emoji = get_rank_emoji(rank['id'])
        keyboard_rows.append([InlineKeyboardButton(
            text=f"{emoji} معاينة أسعار {rank['name']}", 
            callback_data=f"services_preview_{rank['id']}"
        )])
    
    keyboard_rows.append([InlineKeyboardButton(text="🔙 العودة", callback_data="services_management")])
    
    await callback.message.edit_text(
        "💰 <b>معاينة أسعار الخدمات</b>\n\n"
        "اختر الرتبة لمعاينة الأسعار المطبقة على الخدمات:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )

@router.callback_query(F.data.startswith("services_preview_"))
async def show_services_price_preview(callback: CallbackQuery, state: FSMContext):
    """عرض معاينة أسعار الخدمات لرتبة محددة"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    try:
        rank_id = int(callback.data.split("_")[-1])
        
        # الحصول على الخدمات النشطة
        services = await get_services(include_inactive=False)
        
        if not services:
            await callback.message.edit_text(
                "❌ لا توجد خدمات نشطة للمعاينة.\n"
                "قم بمزامنة الخدمات من API أولاً.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 العودة", callback_data="services_price_preview")]
                ])
            )
            return
        
        from database.ranks import get_rank_name, get_rank_emoji
        rank_emoji = get_rank_emoji(rank_id)
        rank_name = get_rank_name(rank_id)
        
        text = f"💰 <b>معاينة أسعار الخدمات - {rank_emoji} {rank_name}</b>\n\n"
        
        # عرض عينة من الخدمات (أول 5 خدمات)
        total_savings = 0
        services_with_discount = 0
        
        for i, service in enumerate(services[:5]):
            pricing = await calculate_service_price(
                service_id=service['id'],
                base_price=service['base_price'],
                user_rank_id=rank_id,
                category_id=service['category_id']
            )
            
            original = pricing['base_price']
            final = pricing['final_price']
            savings = pricing['savings']
            
            if savings > 0:
                services_with_discount += 1
                total_savings += savings
                text += f"🔸 <b>{service['name'][:30]}...</b>\n"
                text += f"  💸 السعر الأصلي: ${original:.2f}\n"
                text += f"  💰 السعر المخفض: ${final:.2f}\n"
                text += f"  ✨ الوفورات: ${savings:.2f}\n\n"
            else:
                text += f"🔸 <b>{service['name'][:30]}...</b> - ${final:.2f}\n\n"
        
        if len(services) > 5:
            text += f"... و {len(services) - 5} خدمة أخرى\n\n"
        
        text += f"📊 <b>ملخص الخصومات:</b>\n"
        text += f"🔹 خدمات مخفضة: {services_with_discount} من {len(services[:5])}\n"
        text += f"🔹 إجمالي الوفورات: ${total_savings:.2f}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 عرض جميع الخدمات", callback_data=f"services_full_preview_{rank_id}")],
            [InlineKeyboardButton(text="🔙 العودة", callback_data="services_price_preview")]
        ])
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"خطأ في معاينة أسعار الخدمات: {e}")
        await callback.answer("❌ حدث خطأ أثناء تحميل معاينة الأسعار.")

# إضافة callback لإدارة الخدمات (placeholder)
@router.callback_query(F.data == "services_management")
async def back_to_services_management(callback: CallbackQuery, state: FSMContext):
    """العودة لإدارة الخدمات"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    # محاكاة message object للاستفادة من نفس الدالة
    class FakeMessage:
        def __init__(self, callback_message):
            self.answer = callback_message.edit_text
            self.from_user = callback.from_user
    
    fake_message = FakeMessage(callback.message)
    await services_management(fake_message, state)