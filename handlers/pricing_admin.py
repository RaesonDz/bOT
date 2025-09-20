"""
معالجات إدارة نظام التسعير للمشرف
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

import config
from database.pricing import (
    create_pricing_rule, get_pricing_rules, update_pricing_rule, 
    delete_pricing_rule, get_pricing_rule_by_id, get_pricing_preview,
    get_pricing_statistics
)
from database.services import get_categories, get_services
from database.ranks import get_all_ranks
from states.order import AdminState
from utils.common import format_money

# إنشاء مسجل
logger = logging.getLogger("smm_bot")

# إنشاء موجه
router = Router(name="pricing_admin")

@router.message(F.text == "💰 إدارة التسعير")
async def pricing_management(message: Message, state: FSMContext):
    """معالج إدارة التسعير الرئيسي"""
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    try:
        # الحصول على إحصائيات التسعير
        stats = await get_pricing_statistics()
        
        # إنشاء رسالة الإحصائيات
        stats_text = f"""
💰 <b>لوحة إدارة التسعير</b>

📊 <b>الإحصائيات:</b>
🔹 <b>القواعد النشطة:</b> {stats['active_rules']}
🔹 <b>متوسط النسبة:</b> {stats['average_percentage']}%

📋 <b>القواعد حسب النطاق:</b>
"""
        
        for scope, count in stats.get('scope_stats', {}).items():
            scope_name = {
                'global': 'عام',
                'category': 'فئة',
                'service': 'خدمة'
            }.get(scope, scope)
            stats_text += f"🔸 {scope_name}: {count}\n"
        
        stats_text += "\nاختر العملية المطلوبة:"
        
        # إنشاء لوحة المفاتيح
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 إضافة قاعدة جديدة", callback_data="pricing_add_rule"),
                InlineKeyboardButton(text="📋 عرض القواعد", callback_data="pricing_view_rules")
            ],
            [
                InlineKeyboardButton(text="👁‍🗨 معاينة الأسعار", callback_data="pricing_preview"),
                InlineKeyboardButton(text="📊 إحصائيات تفصيلية", callback_data="pricing_stats")
            ],
            [
                InlineKeyboardButton(text="🔄 مزامنة الخدمات", callback_data="pricing_sync_services"),
                InlineKeyboardButton(text="🔙 العودة", callback_data="admin_main")
            ]
        ])
        
        await message.answer(
            stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"خطأ في إدارة التسعير: {e}")
        await message.answer("⚠️ حدث خطأ أثناء تحميل معلومات التسعير.")

@router.callback_query(F.data == "pricing_add_rule")
async def add_pricing_rule_start(callback: CallbackQuery, state: FSMContext):
    """بدء إضافة قاعدة تسعير جديدة"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    # اختيار نطاق القاعدة
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌍 عام (جميع الخدمات)", callback_data="pricing_scope_global"),
            InlineKeyboardButton(text="📂 فئة محددة", callback_data="pricing_scope_category")
        ],
        [
            InlineKeyboardButton(text="🎯 خدمة محددة", callback_data="pricing_scope_service"),
            InlineKeyboardButton(text="🔙 العودة", callback_data="pricing_management")
        ]
    ])
    
    await callback.message.edit_text(
        "📝 <b>إضافة قاعدة تسعير جديدة</b>\n\n"
        "اختر نطاق القاعدة:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("pricing_scope_"))
async def select_pricing_scope(callback: CallbackQuery, state: FSMContext):
    """اختيار نطاق قاعدة التسعير"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    scope = callback.data.split("_")[-1]  # global, category, service
    
    await state.update_data(pricing_scope=scope)
    
    if scope == "global":
        # للقاعدة العامة، ننتقل مباشرة لاختيار الرتبة
        await select_rank_for_pricing(callback, state)
    elif scope == "category":
        # عرض قائمة الفئات
        categories = await get_categories(include_inactive=True)
        
        if not categories:
            await callback.message.edit_text(
                "❌ لا توجد فئات متاحة.\nيرجى إضافة فئات أولاً.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 العودة", callback_data="pricing_add_rule")]
                ])
            )
            return
        
        # إنشاء أزرار الفئات
        keyboard_rows = []
        for i in range(0, len(categories), 2):
            row = []
            for j in range(2):
                if i + j < len(categories):
                    category = categories[i + j]
                    row.append(InlineKeyboardButton(
                        text=f"📂 {category['name']}",
                        callback_data=f"pricing_cat_{category['id']}"
                    ))
            keyboard_rows.append(row)
        
        keyboard_rows.append([InlineKeyboardButton(text="🔙 العودة", callback_data="pricing_add_rule")])
        
        await callback.message.edit_text(
            "📂 <b>اختيار الفئة</b>\n\n"
            "اختر الفئة التي تريد تطبيق قاعدة التسعير عليها:",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        )
    
    elif scope == "service":
        # عرض قائمة الخدمات
        services = await get_services(include_inactive=True)
        
        if not services:
            await callback.message.edit_text(
                "❌ لا توجد خدمات متاحة.\nيرجى مزامنة الخدمات أولاً.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 العودة", callback_data="pricing_add_rule")]
                ])
            )
            return
        
        # عرض الخدمات مع التصفح (5 خدمات في كل صفحة)
        page = 0
        services_per_page = 5
        await show_services_page(callback, state, services, page, services_per_page)

async def show_services_page(callback, state, services, page, per_page):
    """عرض صفحة من الخدمات"""
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_services = services[start_idx:end_idx]
    
    keyboard_rows = []
    for service in page_services:
        keyboard_rows.append([InlineKeyboardButton(
            text=f"🎯 {service['name'][:30]}..." if len(service['name']) > 30 else f"🎯 {service['name']}",
            callback_data=f"pricing_svc_{service['id']}"
        )])
    
    # أزرار التنقل
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ السابق", callback_data=f"pricing_svc_page_{page-1}"))
    if end_idx < len(services):
        nav_row.append(InlineKeyboardButton(text="➡️ التالي", callback_data=f"pricing_svc_page_{page+1}"))
    
    if nav_row:
        keyboard_rows.append(nav_row)
    
    keyboard_rows.append([InlineKeyboardButton(text="🔙 العودة", callback_data="pricing_add_rule")])
    
    await state.update_data(services_list=services, current_page=page, per_page=per_page)
    
    await callback.message.edit_text(
        f"🎯 <b>اختيار الخدمة</b>\n\n"
        f"الصفحة {page + 1} من {(len(services) - 1) // per_page + 1}\n"
        "اختر الخدمة التي تريد تطبيق قاعدة التسعير عليها:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )

@router.callback_query(F.data.startswith("pricing_svc_page_"))
async def navigate_services_page(callback: CallbackQuery, state: FSMContext):
    """التنقل بين صفحات الخدمات"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    services = data.get('services_list', [])
    per_page = data.get('per_page', 5)
    
    await show_services_page(callback, state, services, page, per_page)

@router.callback_query(F.data.startswith("pricing_cat_"))
async def select_category_for_pricing(callback: CallbackQuery, state: FSMContext):
    """اختيار فئة للتسعير"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    category_id = int(callback.data.split("_")[-1])
    await state.update_data(pricing_ref_id=category_id)
    
    await select_rank_for_pricing(callback, state)

@router.callback_query(F.data.startswith("pricing_svc_"))
async def select_service_for_pricing(callback: CallbackQuery, state: FSMContext):
    """اختيار خدمة للتسعير"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    service_id = int(callback.data.split("_")[-1])
    await state.update_data(pricing_ref_id=service_id)
    
    await select_rank_for_pricing(callback, state)

async def select_rank_for_pricing(callback, state):
    """اختيار الرتبة لقاعدة التسعير"""
    # الحصول على قائمة الرتب
    ranks = await get_all_ranks()
    
    keyboard_rows = []
    
    # إضافة خيار "جميع الرتب"
    keyboard_rows.append([InlineKeyboardButton(
        text="👥 جميع الرتب", 
        callback_data="pricing_rank_all"
    )])
    
    # إضافة الرتب الفردية
    for rank in ranks:
        from database.ranks import get_rank_emoji
        emoji = get_rank_emoji(rank['id'])
        keyboard_rows.append([InlineKeyboardButton(
            text=f"{emoji} {rank['name']}", 
            callback_data=f"pricing_rank_{rank['id']}"
        )])
    
    keyboard_rows.append([InlineKeyboardButton(text="🔙 العودة", callback_data="pricing_add_rule")])
    
    await callback.message.edit_text(
        "👥 <b>اختيار الرتبة</b>\n\n"
        "اختر الرتبة التي تنطبق عليها قاعدة التسعير:\n"
        "(يمكنك اختيار جميع الرتب أو رتبة محددة)",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )

@router.callback_query(F.data.startswith("pricing_rank_"))
async def select_rank_and_input_values(callback: CallbackQuery, state: FSMContext):
    """اختيار الرتبة وطلب إدخال القيم"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    rank_data = callback.data.split("_")[-1]
    rank_id = None if rank_data == "all" else int(rank_data)
    
    await state.update_data(pricing_rank_id=rank_id)
    
    # طلب إدخال اسم القاعدة والقيم
    await callback.message.edit_text(
        "📝 <b>إدخال تفاصيل قاعدة التسعير</b>\n\n"
        "أرسل تفاصيل القاعدة بالتنسيق التالي:\n\n"
        "<code>اسم القاعدة|النسبة المئوية|الرسوم الثابتة</code>\n\n"
        "<b>مثال:</b>\n"
        "<code>خصم VIP|10|5</code>\n\n"
        "📝 <b>الشرح:</b>\n"
        "• النسبة المئوية: زيادة أو نقصان (مثال: 10 = زيادة 10%, -5 = خصم 5%)\n"
        "• الرسوم الثابتة: مبلغ ثابت يُضاف للسعر (بالدولار)\n\n"
        "💡 <b>نصيحة:</b> استخدم النسب السالبة للخصومات والموجبة للزيادات",
        parse_mode=ParseMode.HTML
    )
    
    await state.set_state(AdminState.adding_pricing_rule)

@router.message(AdminState.adding_pricing_rule)
async def process_pricing_rule_input(message: Message, state: FSMContext):
    """معالجة إدخال قاعدة التسعير"""
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    try:
        # تحليل الإدخال
        parts = message.text.split("|")
        if len(parts) != 3:
            await message.answer(
                "❌ تنسيق خاطئ. يرجى استخدام التنسيق:\n"
                "<code>اسم القاعدة|النسبة المئوية|الرسوم الثابتة</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        rule_name = parts[0].strip()
        percentage = float(parts[1].strip())
        fixed_fee = float(parts[2].strip())
        
        # التحقق من صحة القيم
        if not rule_name:
            await message.answer("❌ اسم القاعدة لا يمكن أن يكون فارغاً.")
            return
        
        if percentage < -90 or percentage > 1000:
            await message.answer("❌ النسبة المئوية يجب أن تكون بين -90% و 1000%.")
            return
        
        if fixed_fee < 0:
            await message.answer("❌ الرسوم الثابتة يجب أن تكون موجبة أو صفر.")
            return
        
        # الحصول على البيانات المخزنة
        data = await state.get_data()
        scope = data.get('pricing_scope')
        ref_id = data.get('pricing_ref_id')
        rank_id = data.get('pricing_rank_id')
        
        # إنشاء قاعدة التسعير
        rule_id = await create_pricing_rule(
            name=rule_name,
            scope=scope,
            ref_id=ref_id,
            rank_id=rank_id,
            percentage=percentage,
            fixed_fee=fixed_fee,
            created_by=message.from_user.id
        )
        
        if rule_id > 0:
            # تحديد النطاق للعرض
            scope_name = {
                'global': 'عام',
                'category': 'فئة',
                'service': 'خدمة'
            }.get(scope, scope)
            
            rank_name = "جميع الرتب"
            if rank_id:
                from database.ranks import get_rank_name
                rank_name = get_rank_name(rank_id)
            
            await message.answer(
                f"✅ <b>تم إنشاء قاعدة التسعير بنجاح!</b>\n\n"
                f"🏷️ <b>الاسم:</b> {rule_name}\n"
                f"🎯 <b>النطاق:</b> {scope_name}\n"
                f"👥 <b>الرتبة:</b> {rank_name}\n"
                f"📊 <b>النسبة:</b> {percentage:+.1f}%\n"
                f"💰 <b>الرسوم الثابتة:</b> ${fixed_fee:.2f}\n"
                f"🆔 <b>معرف القاعدة:</b> {rule_id}",
                parse_mode=ParseMode.HTML
            )
        else:
            await message.answer("❌ حدث خطأ أثناء إنشاء قاعدة التسعير.")
        
    except ValueError:
        await message.answer(
            "❌ قيم غير صحيحة. تأكد من أن النسبة المئوية والرسوم الثابتة أرقام صحيحة."
        )
    except Exception as e:
        logger.error(f"خطأ في معالجة قاعدة التسعير: {e}")
        await message.answer("❌ حدث خطأ أثناء معالجة قاعدة التسعير.")
    
    finally:
        await state.clear()

@router.callback_query(F.data == "pricing_view_rules")
async def view_pricing_rules(callback: CallbackQuery, state: FSMContext):
    """عرض قواعد التسعير الموجودة"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    try:
        # الحصول على جميع القواعد النشطة
        rules = await get_pricing_rules(active_only=True)
        
        if not rules:
            await callback.message.edit_text(
                "📋 <b>قواعد التسعير</b>\n\n"
                "❌ لا توجد قواعد تسعير نشطة حالياً.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ إضافة قاعدة جديدة", callback_data="pricing_add_rule")],
                    [InlineKeyboardButton(text="🔙 العودة", callback_data="pricing_management")]
                ])
            )
            return
        
        # عرض القواعد مع التصفح
        page = 0
        rules_per_page = 3
        await show_rules_page(callback, state, rules, page, rules_per_page)
        
    except Exception as e:
        logger.error(f"خطأ في عرض قواعد التسعير: {e}")
        await callback.answer("❌ حدث خطأ أثناء تحميل القواعد.")

async def show_rules_page(callback, state, rules, page, per_page):
    """عرض صفحة من قواعد التسعير"""
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_rules = rules[start_idx:end_idx]
    
    text = f"📋 <b>قواعد التسعير</b>\n\n"
    text += f"📄 الصفحة {page + 1} من {(len(rules) - 1) // per_page + 1}\n\n"
    
    keyboard_rows = []
    
    for i, rule in enumerate(page_rules):
        # تحديد النطاق
        scope_name = {
            'global': '🌍 عام',
            'category': '📂 فئة',
            'service': '🎯 خدمة'
        }.get(rule['scope'], rule['scope'])
        
        # تحديد الرتبة
        rank_name = "جميع الرتب"
        if rule['rank_id']:
            from database.ranks import get_rank_name, get_rank_emoji
            rank_name = f"{get_rank_emoji(rule['rank_id'])} {get_rank_name(rule['rank_id'])}"
        
        # إضافة معلومات القاعدة
        text += f"<b>🔹 {rule['name']}</b>\n"
        text += f"┣ 🎯 النطاق: {scope_name}\n"
        text += f"┣ 👥 الرتبة: {rank_name}\n"
        text += f"┣ 📊 النسبة: {rule['percentage']:+.1f}%\n"
        text += f"┣ 💰 رسوم ثابتة: ${rule['fixed_fee']:.2f}\n"
        text += f"┗ 🆔 المعرف: {rule['id']}\n\n"
        
        # إضافة أزرار التحكم
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"✏️ تعديل ({rule['id']})", 
                callback_data=f"pricing_edit_{rule['id']}"
            ),
            InlineKeyboardButton(
                text=f"🗑 حذف ({rule['id']})", 
                callback_data=f"pricing_delete_{rule['id']}"
            )
        ])
    
    # أزرار التنقل
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ السابق", callback_data=f"pricing_rules_page_{page-1}"))
    if end_idx < len(rules):
        nav_row.append(InlineKeyboardButton(text="➡️ التالي", callback_data=f"pricing_rules_page_{page+1}"))
    
    if nav_row:
        keyboard_rows.append(nav_row)
    
    # أزرار إضافية
    keyboard_rows.append([
        InlineKeyboardButton(text="➕ إضافة قاعدة جديدة", callback_data="pricing_add_rule"),
        InlineKeyboardButton(text="🔄 تحديث", callback_data="pricing_view_rules")
    ])
    keyboard_rows.append([InlineKeyboardButton(text="🔙 العودة", callback_data="pricing_management")])
    
    await state.update_data(rules_list=rules, current_rules_page=page, rules_per_page=per_page)
    
    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )

@router.callback_query(F.data.startswith("pricing_rules_page_"))
async def navigate_rules_page(callback: CallbackQuery, state: FSMContext):
    """التنقل بين صفحات القواعد"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    rules = data.get('rules_list', [])
    per_page = data.get('rules_per_page', 3)
    
    await show_rules_page(callback, state, rules, page, per_page)

@router.callback_query(F.data == "pricing_preview")
async def pricing_preview(callback: CallbackQuery, state: FSMContext):
    """معاينة الأسعار حسب الرتب"""
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
            callback_data=f"pricing_preview_{rank['id']}"
        )])
    
    keyboard_rows.append([InlineKeyboardButton(text="🔙 العودة", callback_data="pricing_management")])
    
    await callback.message.edit_text(
        "👁‍🗨 <b>معاينة الأسعار</b>\n\n"
        "اختر الرتبة لمعاينة الأسعار المطبقة عليها:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )

@router.callback_query(F.data.startswith("pricing_preview_"))
async def show_pricing_preview(callback: CallbackQuery, state: FSMContext):
    """عرض معاينة الأسعار لرتبة محددة"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    try:
        rank_id = int(callback.data.split("_")[-1])
        
        # الحصول على معاينة الأسعار
        preview = await get_pricing_preview(rank_id)
        
        from database.ranks import get_rank_name, get_rank_emoji
        rank_emoji = get_rank_emoji(rank_id)
        rank_name = get_rank_name(rank_id)
        
        text = f"👁‍🗨 <b>معاينة أسعار {rank_emoji} {rank_name}</b>\n\n"
        text += f"📊 <b>إجمالي الخدمات:</b> {preview['total_services']}\n"
        text += f"💰 <b>إجمالي الوفورات:</b> ${preview['total_savings']:.2f}\n\n"
        
        if not preview['categories']:
            text += "❌ لا توجد خدمات متاحة للمعاينة."
        else:
            # عرض أول 3 فئات فقط للاختصار
            for category in preview['categories'][:3]:
                text += f"📂 <b>{category['name']}</b>\n"
                text += f"💰 وفورات الفئة: ${category['category_savings']:.2f}\n"
                
                # عرض أول 2 خدمات من كل فئة
                for service in category['services'][:2]:
                    original = service['base_price']
                    final = service['final_price']
                    savings = service['savings']
                    
                    if savings > 0:
                        text += f"  🔸 {service['name'][:25]}...\n"
                        text += f"    💸 السعر الأصلي: ${original:.2f}\n"
                        text += f"    💰 السعر النهائي: ${final:.2f}\n"
                        text += f"    ✨ الوفورات: ${savings:.2f}\n"
                    else:
                        text += f"  🔸 {service['name'][:25]}... - ${final:.2f}\n"
                
                if len(category['services']) > 2:
                    text += f"  ... و {len(category['services']) - 2} خدمة أخرى\n"
                text += "\n"
            
            if len(preview['categories']) > 3:
                text += f"... و {len(preview['categories']) - 3} فئة أخرى"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 معاينة تفصيلية", callback_data=f"pricing_detailed_{rank_id}")],
            [InlineKeyboardButton(text="🔙 العودة", callback_data="pricing_preview")]
        ])
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"خطأ في معاينة الأسعار: {e}")
        await callback.answer("❌ حدث خطأ أثناء تحميل معاينة الأسعار.")

@router.callback_query(F.data.startswith("pricing_delete_"))
async def confirm_delete_pricing_rule(callback: CallbackQuery, state: FSMContext):
    """تأكيد حذف قاعدة التسعير"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    rule_id = int(callback.data.split("_")[-1])
    
    # الحصول على معلومات القاعدة
    rule = await get_pricing_rule_by_id(rule_id)
    
    if not rule:
        await callback.answer("❌ قاعدة التسعير غير موجودة.")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 نعم، احذف", callback_data=f"pricing_confirm_delete_{rule_id}"),
            InlineKeyboardButton(text="❌ إلغاء", callback_data="pricing_view_rules")
        ]
    ])
    
    await callback.message.edit_text(
        f"🗑 <b>تأكيد حذف قاعدة التسعير</b>\n\n"
        f"هل أنت متأكد من حذف القاعدة:\n"
        f"<b>{rule['name']}</b>\n\n"
        f"⚠️ <b>تحذير:</b> هذا الإجراء لا يمكن التراجع عنه!",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("pricing_confirm_delete_"))
async def delete_pricing_rule_confirmed(callback: CallbackQuery, state: FSMContext):
    """حذف قاعدة التسعير بعد التأكيد"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    rule_id = int(callback.data.split("_")[-1])
    
    success = await delete_pricing_rule(rule_id)
    
    if success:
        await callback.answer("✅ تم حذف قاعدة التسعير بنجاح.", show_alert=True)
    else:
        await callback.answer("❌ فشل في حذف قاعدة التسعير.", show_alert=True)
    
    # العودة لعرض القواعد
    await view_pricing_rules(callback, state)

@router.callback_query(F.data == "pricing_stats")
async def detailed_pricing_stats(callback: CallbackQuery, state: FSMContext):
    """عرض إحصائيات تفصيلية للتسعير"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    try:
        # الحصول على إحصائيات مفصلة
        stats = await get_pricing_statistics()
        rules = await get_pricing_rules(active_only=False)
        
        active_rules = [r for r in rules if r['is_active']]
        inactive_rules = [r for r in rules if not r['is_active']]
        
        text = f"📊 <b>إحصائيات التسعير التفصيلية</b>\n\n"
        
        text += f"📈 <b>إحصائيات عامة:</b>\n"
        text += f"🔹 إجمالي القواعد: {len(rules)}\n"
        text += f"🔹 القواعد النشطة: {len(active_rules)}\n"
        text += f"🔹 القواعد غير النشطة: {len(inactive_rules)}\n"
        text += f"🔹 متوسط النسبة: {stats['average_percentage']:.2f}%\n\n"
        
        text += f"📋 <b>توزيع القواعد حسب النطاق:</b>\n"
        for scope, count in stats.get('scope_stats', {}).items():
            scope_name = {
                'global': '🌍 عام',
                'category': '📂 فئة',
                'service': '🎯 خدمة'
            }.get(scope, scope)
            text += f"🔸 {scope_name}: {count}\n"
        
        # إحصائيات حسب الرتب
        rank_stats = {}
        for rule in active_rules:
            rank_id = rule['rank_id'] or 'all'
            rank_stats[rank_id] = rank_stats.get(rank_id, 0) + 1
        
        if rank_stats:
            text += f"\n👥 <b>القواعد حسب الرتب:</b>\n"
            for rank_id, count in rank_stats.items():
                if rank_id == 'all':
                    text += f"🔸 جميع الرتب: {count}\n"
                else:
                    from database.ranks import get_rank_name, get_rank_emoji
                    emoji = get_rank_emoji(rank_id)
                    name = get_rank_name(rank_id)
                    text += f"🔸 {emoji} {name}: {count}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 تحديث", callback_data="pricing_stats")],
            [InlineKeyboardButton(text="🔙 العودة", callback_data="pricing_management")]
        ])
        
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"خطأ في الإحصائيات التفصيلية: {e}")
        await callback.answer("❌ حدث خطأ أثناء تحميل الإحصائيات.")

# إضافة دالة لمزامنة الخدمات (سنحتاجها لاحقاً)
@router.callback_query(F.data == "pricing_sync_services")
async def sync_services_from_api(callback: CallbackQuery, state: FSMContext):
    """مزامنة الخدمات من API الخارجي"""
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    
    await callback.answer("🔄 سيتم تطوير هذه الميزة في المرحلة التالية...", show_alert=True)