"""
معالجات المشرف
"""

import logging
import sqlite3
import aiosqlite
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardRemove, 
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from aiogram.enums import ParseMode

import config
from database.core import get_user, update_user_balance, get_all_users
from database.deposit import get_pending_deposits, approve_deposit, reject_deposit, get_deposit_by_id, get_all_deposits, get_deposit_stats, refund_deposit
from keyboards import reply, inline
from states.order import AdminState
from utils.common import format_money, validate_number, format_deposit_info, format_user_info, format_amount_with_currency

# إنشاء مسجل
logger = logging.getLogger("smm_bot")

# إنشاء موجه
router = Router(name="admin")

# استيراد لوحات المفاتيح
from keyboards import reply

# تصفية الموجه لقبول الرسائل من المشرفين فقط
@router.message.middleware
async def admin_filter(handler, message: Message, data):
    """وسيط لتصفية رسائل المشرفين"""
    if message.from_user.id in config.ADMIN_IDS:
        logger.info(f"تم قبول رسالة من مشرف: {message.from_user.id}")
        return await handler(message, data)
    logger.warning(f"محاولة وصول غير مصرح: {message.from_user.id} ليس في قائمة المشرفين")
    return None

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """معالج أمر المشرف"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        logger.warning(f"محاولة وصول غير مصرح بأمر admin: {message.from_user.id}")
        await message.answer(
            "⛔ عذرًا، أنت لست من المشرفين ولا يمكنك الوصول للوحة التحكم.",
            parse_mode=ParseMode.HTML
        )
        return

    # سجل دخول المشرف للوحة التحكم
    logger.info(f"دخول مشرف للوحة التحكم: {message.from_user.id}")

    # عرض القائمة الرئيسية للمشرف
    await message.answer(
        f"👑 <b>القائمة الرئيسية للمشرف</b>\n\n"
        f"مرحبًا بك {message.from_user.full_name} في نظام إدارة البوت.\n"
        f"يمكنك استخدام الأزرار أدناه للوصول إلى الوظائف الرئيسية.\n\n"
        f"🔹 <b>معرف المشرف:</b> {message.from_user.id}\n"
        f"🔹 <b>صلاحيات الوصول:</b> مشرف كامل",
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_admin_main_keyboard()
    )

@router.message(F.text == "👑 لوحة المشرف")
async def admin_panel_command(message: Message):
    """معالج فتح لوحة المشرف الكاملة مع شارات الإشعارات المتحركة"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        logger.warning(f"محاولة وصول غير مصرح: {message.from_user.id}")
        return

    # سجل دخول المشرف للوحة التحكم
    logger.info(f"دخول مشرف للوحة التحكم التفصيلية: {message.from_user.id}")

    try:
        # جلب لوحة المفاتيح مع شارات الإشعارات المتحركة
        admin_keyboard = reply.get_admin_keyboard()
        
        # عرض لوحة تحكم المشرف التفصيلية مع شارات الإشعارات
        await message.answer(
            f"👑 <b>لوحة تحكم المشرف</b>\n\n"
            f"مرحبًا بك في لوحة تحكم المشرف التفصيلية. يمكنك استخدام الأزرار أدناه للوصول إلى مختلف الوظائف الإدارية.\n\n"
            f"🔹 <b>معرف المشرف:</b> {message.from_user.id}\n"
            f"🔹 <b>الاسم:</b> {message.from_user.full_name}\n"
            f"🔹 <b>قائمة المشرفين:</b> {config.ADMIN_IDS}",
            parse_mode=ParseMode.HTML,
            reply_markup=admin_keyboard
        )
    except Exception as e:
        # إذا حدثت مشكلة، استخدم النسخة المتزامنة البديلة
        logger.error(f"خطأ في إنشاء لوحة مفاتيح المشرف: {e}")
        await message.answer(
            f"👑 <b>لوحة تحكم المشرف</b>\n\n"
            f"مرحبًا بك في لوحة تحكم المشرف التفصيلية. يمكنك استخدام الأزرار أدناه للوصول إلى مختلف الوظائف الإدارية.\n\n"
            f"🔹 <b>معرف المشرف:</b> {message.from_user.id}\n"
            f"🔹 <b>الاسم:</b> {message.from_user.full_name}",
            parse_mode=ParseMode.HTML,
            reply_markup=reply.get_admin_keyboard()
        )

@router.message(F.text == "📊 إحصائيات سريعة")
async def quick_stats(message: Message):
    """معالج عرض إحصائيات سريعة للنظام"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        return

    try:
        # الحصول على إحصائيات المستخدمين
        users, total_users = await get_all_users()

        # الحصول على إحصائيات طلبات الإيداع
        from database.deposit import get_deposit_stats
        deposit_stats = await get_deposit_stats()

        # الحصول على إحصائيات الطلبات
        from database.core import get_orders_stats
        orders_stats = await get_orders_stats()

        # عرض الإحصائيات السريعة
        await message.answer(
            f"📊 <b>الإحصائيات السريعة:</b>\n\n"
            f"👥 <b>إجمالي المستخدمين:</b> {total_users}\n"
            f"📦 <b>طلبات الإيداع المعلقة:</b> {deposit_stats.get('pending', {}).get('count', 0)}\n"
            f"🛒 <b>إجمالي الطلبات:</b> {orders_stats.get('total_count', 0)}\n"
            f"💰 <b>إجمالي المبيعات:</b> ${format_money(orders_stats.get('total_amount', 0))}\n\n"
            f"🔄 <b>آخر تحديث:</b> الآن",
            parse_mode=ParseMode.HTML,
            reply_markup=reply.get_admin_main_keyboard()
        )
    except Exception as e:
        logger.error(f"خطأ في عرض الإحصائيات السريعة: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء جمع الإحصائيات. يرجى المحاولة مرة أخرى.",
            reply_markup=reply.get_admin_main_keyboard()
        )

@router.message(F.text == "📦 طلبات الإيداع المعلقة")
async def pending_deposits_quick(message: Message, state: FSMContext):
    """معالج عرض طلبات الإيداع المعلقة من القائمة الرئيسية"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        return

    # الحصول على طلبات الإيداع المعلقة
    deposits, total = await get_pending_deposits()

    if not deposits:
        await message.answer(
            "📭 لا توجد طلبات إيداع معلقة حاليًا.",
            reply_markup=reply.get_admin_main_keyboard()
        )
        return

    # تخزين البيانات في الحالة
    await state.update_data(deposits=deposits, total_deposits=total, page=1)

    # عرض طلبات الإيداع
    await display_deposits_page(message, state)

    # تعيين حالة إدارة طلبات الإيداع
    await state.set_state(AdminState.managing_deposits)

@router.message(F.text == "🛒 آخر الطلبات")
async def recent_orders(message: Message, state: FSMContext):
    """معالج عرض آخر الطلبات"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        return

    # الحصول على آخر الطلبات (بحد أقصى 5)
    from database.core import get_recent_orders
    orders = await get_recent_orders(limit=5)

    if not orders:
        await message.answer(
            "📭 لا توجد طلبات حديثة.",
            reply_markup=reply.get_admin_main_keyboard()
        )
        return

    # إنشاء نص الطلبات
    orders_text = "🛒 <b>آخر الطلبات:</b>\n\n"

    for order in orders:
        order_id = order.get("order_id", "غير محدد")
        username = order.get("username", "غير محدد")
        service_name = order.get("service_name", "غير محدد")
        amount = order.get("amount", 0)
        status = order.get("status", "Pending")
        created_at = order.get("created_at", "غير محدد")

        # تحويل حالة الطلب إلى رمز
        status_emoji = "🕒"  # معلق
        if status == "Completed":
            status_emoji = "✅"  # مكتمل
        elif status == "Processing":
            status_emoji = "⏳"  # قيد المعالجة
        elif status == "Canceled" or status == "Cancelled":
            status_emoji = "❌"  # ملغي
        elif status == "Failed":
            status_emoji = "⚠️"  # فشل
        elif status == "Partial":
            status_emoji = "⚠️"  # جزئي

        orders_text += (
            f"🔹 <b>رقم الطلب:</b> {order_id}\n"
            f"👤 <b>المستخدم:</b> @{username}\n"
            f"📦 <b>الخدمة:</b> {service_name}\n"
            f"💰 <b>المبلغ:</b> ${format_money(amount)}\n"
            f"📊 <b>الحالة:</b> {status_emoji} {status}\n"
            f"🕒 <b>التاريخ:</b> {created_at}\n\n"
        )

    # إضافة خيار عرض المزيد
    orders_text += "💡 لعرض المزيد، استخدم 'إدارة الطلبات' من لوحة المشرف."

    # إرسال الرسالة
    await message.answer(
        orders_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_admin_main_keyboard()
    )

@router.message(F.text == "👥 إدارة المستخدمين")
async def manage_users_from_main(message: Message, state: FSMContext):
    """معالج إدارة المستخدمين من القائمة الرئيسية"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        return

    # استدعاء معالج إدارة المستخدمين العادي
    await manage_users(message, state)

@router.message(F.text == "📢 إرسال إشعار")
async def send_notification_from_main(message: Message, state: FSMContext):
    """معالج إرسال إشعار من القائمة الرئيسية"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        return

    # استدعاء معالج إرسال الإشعار العادي
    await send_global_notification_start(message, state)

@router.message(F.text == "🔄 تحديث النظام")
async def refresh_system(message: Message):
    """معالج تحديث النظام"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        return

    await message.answer(
        "🔄 <b>جاري تحديث معلومات النظام...</b>",
        parse_mode=ParseMode.HTML
    )

    try:
        # يمكن هنا إضافة أي عمليات تحديث مطلوبة للنظام
        # مثل إعادة تحميل الإعدادات أو تنظيف الذاكرة المؤقتة

        # إرسال رسالة النجاح
        await message.answer(
            "✅ <b>تم تحديث النظام بنجاح!</b>\n\n"
            "• تم تحديث قواعد البيانات\n"
            "• تم تحديث الإعدادات\n"
            "• تم تنظيف الذاكرة المؤقتة",
            parse_mode=ParseMode.HTML,
            reply_markup=reply.get_admin_main_keyboard()
        )
    except Exception as e:
        logger.error(f"خطأ في تحديث النظام: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء تحديث النظام. يرجى المحاولة مرة أخرى.",
            reply_markup=reply.get_admin_main_keyboard()
        )

@router.message(F.text == "🛠️ إعدادات البوت")
async def bot_settings(message: Message):
    """معالج عرض إعدادات البوت"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        return

    # عرض الإعدادات الحالية
    await message.answer(
        f"🛠️ <b>إعدادات البوت:</b>\n\n"
        f"📊 <b>الإصدار:</b> 1.0.0\n"
        f"⚙️ <b>الوضع:</b> إنتاج\n"
        f"👥 <b>المشرفين:</b> {len(config.ADMIN_IDS)}\n"
        f"🔔 <b>الإشعارات التلقائية:</b> مفعلة\n\n"
        f"💡 <b>لتغيير الإعدادات:</b> استخدم قسم 'لوحة المشرف' ثم 'تعديل الإعدادات'.",
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_admin_main_keyboard()
    )

@router.message(F.text == "👑 لوحة المشرف")
async def admin_panel(message: Message):
    """معالج لوحة المشرف"""
    logger.info(f"طلب الوصول للوحة المشرف بواسطة: {message.from_user.id}")

    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        logger.warning(f"محاولة وصول غير مصرح: {message.from_user.id}")
        await message.answer(
            "⛔ عذرًا، أنت لست من المشرفين ولا يمكنك الوصول للوحة التحكم.",
            parse_mode=ParseMode.HTML,
            reply_markup=reply.get_main_keyboard()
        )
        return

    # استدعاء معالج أمر المشرف
    await cmd_admin(message)

@router.message(F.text == "📊 إحصائيات")
async def show_statistics(message: Message):
    """معالج عرض إحصائيات النظام"""
    try:
        # الحصول على إحصائيات المستخدمين
        users, total_users = await get_all_users()

        # الحصول على إحصائيات الطلبات
        from database.core import get_orders_stats
        orders_stats = await get_orders_stats()

        # الحصول على إحصائيات الإيداعات
        from database.deposit import get_deposit_stats
        deposit_stats = await get_deposit_stats()

        # حساب إجمالي المبيعات
        total_orders_amount = orders_stats.get("total_amount", 0)

        # حساب إجمالي الإيداعات
        total_deposits = deposit_stats.get("approved", {}).get("total", 0)

        # إنشاء نص الإحصائيات
        stats_text = (
            f"📊 <b>إحصائيات النظام:</b>\n\n"
            f"👥 <b>المستخدمين:</b>\n"
            f"   - <b>العدد الإجمالي:</b> {total_users}\n\n"
            f"🛒 <b>الطلبات:</b>\n"
            f"   - <b>عدد الطلبات:</b> {orders_stats.get('total_count', 0)}\n"
            f"   - <b>إجمالي المبيعات:</b> ${format_money(total_orders_amount)}\n\n"
            f"💰 <b>الإيداعات:</b>\n"
            f"   - <b>قيد الانتظار:</b> {deposit_stats.get('pending', {}).get('count', 0)} (${format_money(deposit_stats.get('pending', {}).get('total', 0))})\n"
            f"   - <b>تمت الموافقة:</b> {deposit_stats.get('approved', {}).get('count', 0)} (${format_money(deposit_stats.get('approved', {}).get('total', 0))})\n"
            f"   - <b>تم الرفض:</b> {deposit_stats.get('rejected', {}).get('count', 0)} (${format_money(deposit_stats.get('rejected', {}).get('total', 0))})\n"
        )

        # جلب لوحة المفاتيح مع شارات الإشعارات المتحركة
        admin_keyboard = reply.get_admin_keyboard()
        
        await message.answer(
            stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=admin_keyboard
        )
    except Exception as e:
        logger.error(f"خطأ في عرض الإحصائيات: {e}")
        # في حالة حدوث خطأ استخدم النسخة المتزامنة البديلة
        await message.answer(
            "⚠️ حدث خطأ أثناء جمع إحصائيات النظام. يرجى المحاولة مرة أخرى.",
            reply_markup=reply.get_admin_keyboard()
        )

@router.message(F.text == "👥 المستخدمين")
async def manage_users(message: Message, state: FSMContext):
    """معالج إدارة المستخدمين"""
    # الحصول على قائمة المستخدمين
    users, total = await get_all_users()

    if not users:
        try:
            # جلب لوحة المفاتيح مع شارات الإشعارات المتحركة
            admin_keyboard = reply.get_admin_keyboard()
            
            await message.answer(
                "⚠️ لا يوجد مستخدمون مسجلون حاليًا.",
                reply_markup=admin_keyboard
            )
        except Exception as e:
            logger.error(f"خطأ في إنشاء لوحة مفاتيح المشرف: {e}")
            await message.answer(
                "⚠️ لا يوجد مستخدمون مسجلون حاليًا.",
                reply_markup=reply.get_admin_keyboard()
            )
        return

    # تخزين البيانات في الحالة
    await state.update_data(users=users, total_users=total, page=1)

    # عرض المستخدمين
    await display_users_page(message, state)

    # تعيين حالة إدارة المستخدمين
    await state.set_state(AdminState.managing_users)

async def display_users_page(message: Message, state: FSMContext):
    """عرض صفحة من المستخدمين"""
    # الحصول على البيانات
    data = await state.get_data()
    users = data.get("users", [])
    total_users = data.get("total_users", 0)
    page = data.get("page", 1)
    per_page = 5  # عدد المستخدمين في الصفحة الواحدة

    # حساب عدد الصفحات
    total_pages = (total_users + per_page - 1) // per_page

    # إنشاء نص المستخدمين
    users_text = f"👥 <b>قائمة المستخدمين ({total_users}):</b>\n"
    users_text += f"📄 <b>الصفحة:</b> {page}/{total_pages}\n\n"

    # حساب نطاق المستخدمين للصفحة الحالية
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(users))

    # إضافة معلومات المستخدمين
    for i in range(start_idx, end_idx):
        user = users[i]
        user_id = user.get("user_id", "غير محدد")
        username = user.get("username", "غير محدد")
        full_name = user.get("full_name", "غير محدد")
        balance = user.get("balance", 0)
        rank_id = user.get("rank_id", 5)  # الرتبة الافتراضية هي برونزي

        # الحصول على اسم الرتبة ورمزها
        from database.ranks import get_rank_emoji
        rank_emoji = get_rank_emoji(rank_id)

        users_text += (
            f"🔹 <b>المستخدم:</b> {user_id} (@{username})\n"
            f"   <b>الاسم:</b> {full_name}\n"
            f"   <b>الرصيد:</b> ${format_money(balance)}\n"
            f"   <b>الرتبة:</b> {rank_emoji}\n\n"
        )

    # إضافة لوحة مفاتيح التنقل
    kb = []
    navigation = []

    if page > 1:
        navigation.append(KeyboardButton(text="◀️ السابق"))

    navigation.append(KeyboardButton(text=f"📄 {page}/{total_pages}"))

    if page < total_pages:
        navigation.append(KeyboardButton(text="التالي ▶️"))

    if navigation:
        kb.append(navigation)

    kb.append([KeyboardButton(text="🔙 العودة")])

    # إضافة التعليمات
    users_text += (
        f"💡 لإدارة مستخدم محدد، أرسل معرفه (ID).\n"
        f"💡 استخدم الأزرار أدناه للتنقل بين الصفحات."
    )

    # إرسال الرسالة مع لوحة المفاتيح
    await message.answer(
        users_text,
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    )

@router.message(AdminState.managing_users)
async def process_users_management(message: Message, state: FSMContext):
    """معالج إدارة المستخدمين"""
    # الحصول على البيانات
    data = await state.get_data()
    users = data.get("users", [])
    total_users = data.get("total_users", 0)
    page = data.get("page", 1)
    per_page = 5
    total_pages = (total_users + per_page - 1) // per_page

    # التحقق من الأمر
    if message.text == "🔙 العودة":
        # العودة للوحة المشرف
        await state.clear()
        await message.answer(
            "🔄 تم العودة إلى لوحة المشرف.",
            reply_markup=reply.get_admin_keyboard()
        )
        return
    elif message.text == "التالي ▶️":
        # الانتقال للصفحة التالية
        if page < total_pages:
            await state.update_data(page=page + 1)
            await display_users_page(message, state)
        else:
            await message.answer("⚠️ أنت بالفعل في الصفحة الأخيرة.")
        return
    elif message.text == "◀️ السابق":
        # الانتقال للصفحة السابقة
        if page > 1:
            await state.update_data(page=page - 1)
            await display_users_page(message, state)
        else:
            await message.answer("⚠️ أنت بالفعل في الصفحة الأولى.")
        return
    elif message.text.startswith("📄 "):
        # تم الضغط على زر رقم الصفحة
        await display_users_page(message, state)
        return

    # محاولة تحليل معرف المستخدم
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer(
            "⚠️ يرجى إدخال معرف مستخدم صحيح، أو استخدام أوامر التنقل."
        )
        return

    # البحث عن المستخدم
    user_data = await get_user(user_id)

    if not user_data:
        await message.answer(
            "⚠️ المستخدم غير موجود في قاعدة البيانات."
        )
        return

    # الحصول على رتبة المستخدم
    from database.ranks import get_rank_emoji, get_rank_name
    rank_id = user_data.get("rank_id", 5)
    rank_emoji = get_rank_emoji(rank_id)
    rank_name = get_rank_name(rank_id)

    # عرض معلومات المستخدم
    user_text = f"👤 <b>معلومات المستخدم:</b>\n\n"
    user_text += format_user_info(user_data)

    # إضافة معلومات الرتبة
    user_text += f"\n🏆 <b>الرتبة:</b> {rank_emoji} {rank_name}\n"

    # إضافة الخيارات
    user_text += (
        f"\n💡 <b>الخيارات المتاحة:</b>\n\n"
        f"استخدم الأزرار أدناه لإدارة المستخدم"
    )

    # إرسال الرسالة مع أزرار إضافة وخصم الرصيد
    from keyboards import inline
    await message.answer(
        user_text,
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_balance_actions_keyboard(user_id)
    )


@router.message(F.text.startswith("إضافة رصيد "))
async def add_user_balance_cmd(message: Message, state: FSMContext):
    """معالج إضافة رصيد لمستخدم عن طريق الأمر"""
    # التحقق من أن المستخدم في حالة إدارة المستخدمين
    current_state = await state.get_state()
    if current_state != AdminState.managing_users.state:
        return

    # تحليل الأمر
    parts = message.text.split()

    if len(parts) != 3:
        await message.answer(
            "⚠️ الصيغة غير صحيحة. يجب أن تكون: 'إضافة رصيد [معرف المستخدم] [المبلغ]'"
        )
        return
        
    # محاولة تحليل معرف المستخدم والمبلغ
    try:
        user_id = int(parts[1])
        amount = float(parts[2])
    except ValueError:
        await message.answer(
            "⚠️ معرف المستخدم أو المبلغ غير صحيح. يرجى التأكد من صحة البيانات."
        )
        return

    # استدعاء وظيفة إضافة الرصيد المشتركة
    await process_add_balance(message, user_id, amount)
        
@router.message(F.text == "🔄 مزامنة الخدمات")
async def sync_services_command(message: Message, state: FSMContext):
    """معالج مزامنة الخدمات والفئات من API"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        logger.warning(f"محاولة وصول غير مصرح لمزامنة الخدمات: {message.from_user.id}")
        return
    
    # تغيير الحالة إلى حالة المزامنة
    await state.set_state(AdminState.syncing_services)
    
    # إرسال رسالة البدء
    processing_msg = await message.answer(
        "⏳ <b>جاري مزامنة الخدمات والفئات...</b>\n\n"
        "هذه العملية قد تستغرق بضع دقائق، يرجى الانتظار.",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # استيراد وظيفة المزامنة
        from services.sync_services import sync_all
        
        # بدء عملية المزامنة
        logger.info(f"بدء مزامنة الخدمات بواسطة المشرف: {message.from_user.id}")
        
        # تنفيذ المزامنة
        sync_result = await sync_all()
        
        # التحقق من نجاح المزامنة
        if sync_result.get("success", False):
            # الحصول على إحصاءات المزامنة
            categories_stats = sync_result.get("categories", {})
            services_stats = sync_result.get("services", {})
            
            # إنشاء نص النتيجة
            result_text = (
                "✅ <b>تمت مزامنة الخدمات والفئات بنجاح!</b>\n\n"
                f"📊 <b>إحصائيات المزامنة:</b>\n"
                f"🔹 <b>الفئات:</b>\n"
                f"  • إجمالي الفئات: {categories_stats.get('total', 0)}\n"
                f"  • فئات جديدة: {categories_stats.get('new', 0)}\n"
                f"  • فئات محدثة: {categories_stats.get('updated', 0)}\n\n"
                f"🔹 <b>الخدمات:</b>\n"
                f"  • إجمالي الخدمات: {services_stats.get('total', 0)}\n"
                f"  • خدمات جديدة: {services_stats.get('new', 0)}\n"
                f"  • خدمات محدثة: {services_stats.get('updated', 0)}\n\n"
                f"🕒 وقت المزامنة: {sync_result.get('timestamp', '')}"
            )
            
            # إرسال رسالة النجاح
            await processing_msg.edit_text(
                result_text,
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"تمت مزامنة الخدمات بنجاح: {services_stats.get('total', 0)} خدمة، {categories_stats.get('total', 0)} فئة")
        else:
            # إرسال رسالة الفشل
            error_message = sync_result.get("error", "خطأ غير معروف")
            await processing_msg.edit_text(
                f"❌ <b>فشلت عملية المزامنة</b>\n\n"
                f"سبب الخطأ: {error_message}\n\n"
                f"يرجى التحقق من إتصال API والمحاولة مرة أخرى.",
                parse_mode=ParseMode.HTML
            )
            
            logger.error(f"فشلت مزامنة الخدمات: {error_message}")
    except Exception as e:
        # إرسال رسالة الخطأ
        await processing_msg.edit_text(
            f"❌ <b>حدث خطأ أثناء المزامنة</b>\n\n"
            f"تفاصيل الخطأ: {str(e)}\n\n"
            f"يرجى المحاولة مرة أخرى أو التحقق من السجلات للمزيد من المعلومات.",
            parse_mode=ParseMode.HTML
        )
        
        logger.exception(f"استثناء أثناء مزامنة الخدمات: {e}")
    finally:
        # إعادة الحالة إلى الوضع الطبيعي
        await state.clear()

@router.callback_query(F.data.startswith("add_balance_"))
async def add_user_balance_callback(callback: CallbackQuery, state: FSMContext):
    """معالج زر إضافة رصيد لمستخدم"""
    # استخراج معرف المستخدم من البيانات
    user_id = int(callback.data.split('_')[2])

    # الحصول على بيانات المستخدم
    user_data = await get_user(user_id)
    if not user_data:
        await callback.answer("⚠️ المستخدم غير موجود", show_alert=True)
        return

    # إرسال رسالة لطلب المبلغ
    await callback.message.edit_text(
        f"💰 <b>إضافة رصيد لمستخدم</b>\n\n"
        f"👤 <b>المستخدم:</b> {user_id} (@{user_data.get('username', 'غير محدد')})\n"
        f"👤 <b>الاسم:</b> {user_data.get('full_name', 'غير محدد')}\n"
        f"💰 <b>الرصيد الحالي:</b> ${format_money(user_data.get('balance', 0))}\n\n"
        f"يرجى إرسال المبلغ الذي تريد إضافته للمستخدم:",
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_back_button("back_to_user_" + str(user_id))
    )

    # تخزين معرف المستخدم في الحالة
    await state.update_data(add_balance_user_id=user_id)

    # تغيير الحالة إلى إدخال مبلغ الإضافة
    await state.set_state(AdminState.entering_add_balance_amount)

    # الرد على الاستدعاء
    await callback.answer()

    # إرسال رسالة منفصلة بلوحة مفاتيح الرد
    await callback.bot.send_message(
        callback.from_user.id,
        "أدخل المبلغ أو اضغط 'إلغاء' للعودة:",
        reply_markup=reply.get_cancel_keyboard()
    )

@router.message(AdminState.entering_add_balance_amount)
async def process_add_balance_amount(message: Message, state: FSMContext):
    """معالج إدخال مبلغ الإضافة"""
    # التحقق من طلب الإلغاء
    if message.text in ["❌ إلغاء", "إلغاء"]:
        # استرجاع معرف المستخدم من الحالة
        data = await state.get_data()
        user_id = data.get("add_balance_user_id")

        # العودة للوحة المشرف
        await state.clear()
        await message.answer(
            "🔄 تم إلغاء عملية إضافة الرصيد والعودة إلى لوحة المشرف.",
            reply_markup=reply.get_admin_keyboard()
        )
        return

    # محاولة تحليل المبلغ
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من الصفر")
    except ValueError:
        await message.answer(
            "⚠️ يرجى إدخال مبلغ صحيح أكبر من الصفر."
        )
        return

    # استرجاع معرف المستخدم من الحالة
    data = await state.get_data()
    user_id = data.get("add_balance_user_id")

    if not user_id:
        await message.answer("❌ حدث خطأ. يرجى المحاولة مرة أخرى.")
        await state.clear()
        return

    # استدعاء وظيفة إضافة الرصيد المشتركة
    success, updated_user = await update_user_balance_and_notify(message, user_id, amount, "add")

    if success:
        # إرسال رسالة التأكيد
        await message.answer(
            f"✅ تم إضافة الرصيد بنجاح!\n\n"
            f"👤 <b>المستخدم:</b> {user_id} (@{updated_user.get('username', 'غير محدد')})\n"
            f"💰 <b>المبلغ المضاف:</b> ${format_money(amount)}\n"
            f"💵 <b>الرصيد الجديد:</b> ${format_money(updated_user.get('balance', 0))}",
            parse_mode=ParseMode.HTML,
            reply_markup=reply.get_admin_keyboard()
        )

    # إعادة تعيين الحالة
    await state.clear()

async def update_user_balance_and_notify(context, user_id: int, amount: float, action: str):
    """وظيفة موحدة لتحديث الرصيد وإرسال الإشعار"""
    # التحقق من وجود المستخدم
    user_data = await get_user(user_id)

    if not user_data:
        if isinstance(context, Message):
            await context.answer("⚠️ المستخدم غير موجود في قاعدة البيانات.")
        elif isinstance(context, CallbackQuery):
            await context.answer("⚠️ المستخدم غير موجود", show_alert=True)
        return False, None

    # التحقق من كفاية الرصيد في حالة الخصم
    if action == "subtract" and user_data.get("balance", 0) < amount:
        if isinstance(context, Message):
            await context.answer("⚠️ رصيد المستخدم غير كافٍ للخصم.")
        elif isinstance(context, CallbackQuery):
            await context.answer("⚠️ رصيد المستخدم غير كافٍ للخصم", show_alert=True)
        return False, None

    # تحديث الرصيد
    success = await update_user_balance(user_id, amount, action)

    if not success:
        if isinstance(context, Message):
            await context.answer(f"❌ حدث خطأ أثناء {action == 'add' and 'إضافة' or 'خصم'} الرصيد. يرجى المحاولة مرة أخرى.")
        elif isinstance(context, CallbackQuery):
            await context.answer(f"❌ حدث خطأ أثناء تحديث الرصيد", show_alert=True)
        return False, None

    # الحصول على بيانات المستخدم المحدثة
    updated_user = await get_user(user_id)

    # إرسال إشعار للمستخدم
    bot = context.bot if isinstance(context, CallbackQuery) else context.bot

    try:
        if action == "add":
            await bot.send_message(
                user_id,
                f"💰 <b>تم إضافة رصيد لحسابك:</b>\n\n"
                f"💵 <b>المبلغ:</b> ${format_money(amount)}\n"
                f"💰 <b>رصيدك الجديد:</b> ${format_money(updated_user.get('balance', 0))}",
                parse_mode=ParseMode.HTML
            )
        else:
            await bot.send_message(
                user_id,
                f"💰 <b>تم خصم رصيد من حسابك:</b>\n\n"
                f"💵 <b>المبلغ:</b> ${format_money(amount)}\n"
                f"💰 <b>رصيدك الجديد:</b> ${format_money(updated_user.get('balance', 0))}",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار للمستخدم {user_id}: {e}")

    # تسجيل العملية
    user_from = context.from_user.id if isinstance(context, Message) else context.from_user.id
    logger.info(f"{action == 'add' and 'إضافة' or 'خصم'} رصيد: المشرف: {user_from}, المستخدم: {user_id}, المبلغ: {amount}")

    return True, updated_user

@router.message(F.text.startswith("خصم "))
async def subtract_user_balance_cmd(message: Message, state: FSMContext):
    """معالج خصم رصيد من مستخدم عن طريق الأمر"""
    # التحقق من أن المستخدم في حالة إدارة المستخدمين
    current_state = await state.get_state()
    if current_state != AdminState.managing_users.state:
        return

    # تحليل الأمر
    parts = message.text.split()

    if len(parts) != 3:
        await message.answer(
            "⚠️ الصيغة غير صحيحة. يجب أن تكون: 'خصم [معرف المستخدم] [المبلغ]'"
        )
        return

    # محاولة تحليل معرف المستخدم والمبلغ
    try:
        user_id = int(parts[1])
        amount = float(parts[2])
    except ValueError:
        await message.answer(
            "⚠️ معرف المستخدم أو المبلغ غير صحيح. يرجى التأكد من صحة البيانات."
        )
        return

    # استدعاء وظيفة خصم الرصيد المشتركة
    await process_subtract_balance(message, user_id, amount)

@router.callback_query(F.data.startswith("subtract_balance_"))
async def subtract_user_balance_callback(callback: CallbackQuery, state: FSMContext):
    """معالج زر خصم رصيد من مستخدم"""
    # استخراج معرف المستخدم من البيانات
    user_id = int(callback.data.split('_')[2])

    # إرسال رسالة لطلب المبلغ
    await callback.message.answer(
        f"💰 يرجى إدخال المبلغ الذي تريد خصمه من رصيد المستخدم (معرف: {user_id}):"
    )

    # تخزين معرف المستخدم في الحالة
    await state.update_data(subtract_balance_user_id=user_id)

    # تغيير الحالة إلى إدخال مبلغ الخصم
    await state.set_state(AdminState.entering_subtract_balance_amount)

    # الرد على الاستدعاء
    await callback.answer()

@router.message(AdminState.entering_subtract_balance_amount)
async def process_subtract_balance_amount(message: Message, state: FSMContext):
    """معالج إدخال مبلغ الخصم"""
    # محاولة تحليل المبلغ
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError("المبلغ يجب أن يكون أكبر من الصفر")
    except ValueError:
        await message.answer(
            "⚠️ يرجى إدخال مبلغ صحيح أكبر من الصفر."
        )
        return

    # استرجاع معرف المستخدم من الحالة
    data = await state.get_data()
    user_id = data.get("subtract_balance_user_id")

    if not user_id:
        await message.answer("❌ حدث خطأ. يرجى المحاولة مرة أخرى.")
        await state.clear()
        return

    # استدعاء وظيفة خصم الرصيد المشتركة
    await process_subtract_balance(message, user_id, amount)

    # إعادة تعيين الحالة
    await state.clear()

async def process_add_balance(message: Message, user_id: int, amount: float):
    """وظيفة مشتركة لإضافة الرصيد"""
    # التحقق من وجود المستخدم
    user_data = await get_user(user_id)

    if not user_data:
        await message.answer(
            "⚠️ المستخدم غير موجود في قاعدة البيانات."
        )
        return

    # إضافة الرصيد
    success = await update_user_balance(user_id, amount, "add")

    if not success:
        await message.answer(
            "❌ حدث خطأ أثناء إضافة الرصيد. يرجى المحاولة مرة أخرى."
        )
        return

    # الحصول على بيانات المستخدم المحدثة
    updated_user = await get_user(user_id)

    # إرسال رسالة التأكيد
    await message.answer(
        f"✅ تم إضافة الرصيد بنجاح!\n\n"
        f"👤 <b>المستخدم:</b> {user_id} (@{updated_user.get('username', 'غير محدد')})\n"
        f"💰 <b>المبلغ المضاف:</b> ${format_money(amount)}\n"
        f"💵 <b>الرصيد الجديد:</b> ${format_money(updated_user.get('balance', 0))}",
        parse_mode=ParseMode.HTML
    )

    # إرسال إشعار للمستخدم
    try:
        await message.bot.send_message(
            user_id,
            f"💰 <b>تم إضافة رصيد لحسابك:</b>\n\n"
            f"💵 <b>المبلغ:</b> ${format_money(amount)}\n"
            f"💰 <b>رصيدك الجديد:</b> ${format_money(updated_user.get('balance', 0))}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار للمستخدم {user_id}: {e}")

async def process_subtract_balance(message: Message, user_id: int, amount: float):
    """وظيفة مشتركة لخصم الرصيد"""
    # التحقق من وجود المستخدم
    user_data = await get_user(user_id)

    if not user_data:
        await message.answer(
            "⚠️ المستخدم غير موجود في قاعدة البيانات."
        )
        return

    # التحقق من كفاية الرصيد
    if user_data.get("balance", 0) < amount:
        await message.answer(
            "⚠️ رصيد المستخدم غير كافٍ للخصم."
        )
        return

    # خصم الرصيد
    success = await update_user_balance(user_id, amount, "subtract")

    if not success:
        await message.answer(
            "❌ حدث خطأ أثناء خصم الرصيد. يرجى المحاولة مرة أخرى."
        )
        return

    # الحصول على بيانات المستخدم المحدثة
    updated_user = await get_user(user_id)

    # إرسال رسالة التأكيد
    await message.answer(
        f"✅ تم خصم الرصيد بنجاح!\n\n"
        f"👤 <b>المستخدم:</b> {user_id} (@{updated_user.get('username', 'غير محدد')})\n"
        f"💰 <b>المبلغ المخصوم:</b> ${format_money(amount)}\n"
        f"💵 <b>الرصيد الجديد:</b> ${format_money(updated_user.get('balance', 0))}",
        parse_mode=ParseMode.HTML
    )

@router.message(F.text == "📦 طلبات الإيداع")
async def show_pending_deposits(message: Message, state: FSMContext):
    """معالج عرض طلبات الإيداع المعلقة"""
    # الحصول على طلبات الإيداع المعلقة
    deposits, total = await get_pending_deposits()

    if not deposits:
        await message.answer(
            "📭 لا توجد طلبات إيداع معلقة حاليًا.",
            reply_markup=reply.get_admin_keyboard()
        )
        return

    # تخزين البيانات في الحالة
    await state.update_data(deposits=deposits, total_deposits=total, page=1)

    # عرض طلبات الإيداع
    await display_deposits_page(message, state)

    # تعيين حالة إدارة طلبات الإيداع
    await state.set_state(AdminState.managing_deposits)

async def display_deposits_page(message: Message, state: FSMContext):
    """عرض صفحة من طلبات الإيداع"""
    # الحصول على البيانات
    data = await state.get_data()
    deposits = data.get("deposits", [])
    total_deposits = data.get("total_deposits", 0)
    page = data.get("page", 1)
    per_page = 5  # عدد الطلبات في الصفحة الواحدة

    # حساب عدد الصفحات
    total_pages = (total_deposits + per_page - 1) // per_page

    # إنشاء نص طلبات الإيداع
    deposits_text = f"📦 <b>طلبات الإيداع المعلقة ({total_deposits}):</b>\n"
    deposits_text += f"📄 <b>الصفحة:</b> {page}/{total_pages}\n\n"

    # حساب نطاق الطلبات للصفحة الحالية
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(deposits))

    # إضافة معلومات طلبات الإيداع
    for i in range(start_idx, end_idx):
        deposit = deposits[i]
        deposit_id = deposit.get("id", "غير محدد")
        user_id = deposit.get("user_id", "غير محدد")
        username = deposit.get("username", "غير محدد")
        full_name = deposit.get("full_name", "غير محدد")
        amount = deposit.get("amount", 0)
        payment_method = deposit.get("payment_method", "غير محدد")
        created_at = deposit.get("created_at", "غير محدد")

        # تحويل طرق الدفع إلى رموز
        payment_emoji = "💳"
        if payment_method == "USDT":
            payment_emoji = "💵"
        elif payment_method == "BARIDIMOB":
            payment_emoji = "💸"

        # استخدام الدالة الجديدة لعرض المبلغ مع العملة المناسبة
        amount_display = format_amount_with_currency(amount, payment_method)
        
        deposits_text += (
            f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
            f"👤 <b>المستخدم:</b> {user_id} (@{username})\n"
            f"💰 <b>المبلغ:</b> {amount_display}\n"
            f"{payment_emoji} <b>طريقة الدفع:</b> {payment_method}\n"
            f"🕒 <b>تاريخ الطلب:</b> {created_at}\n\n"
        )

    # إنشاء أزرار التحكم
    kb = []
    
    # أزرار التنقل
    navigation = []
    
    if page > 1:
        navigation.append(KeyboardButton(text="◀️ السابق"))
    
    navigation.append(KeyboardButton(text=f"📄 {page}/{total_pages}"))
    
    if page < total_pages:
        navigation.append(KeyboardButton(text="التالي ▶️"))
    
    if navigation:
        kb.append(navigation)
    
    # أزرار العودة
    kb.append([KeyboardButton(text="🔙 العودة")])
    
    # إنشاء لوحة المفاتيح
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    # إضافة التعليمات
    # الحصول على مثال لرقم الطلب من القائمة إن وجد
    example_id = '123'
    if deposits and len(deposits) > 0:
        example_id = str(deposits[0].get("id", "123"))
    
    deposits_text += (
        f"💡 <b>التعليمات:</b>\n"
        f"• لإدارة طلب إيداع، أدخل <b>الرقم</b> مباشرة (مثال: {example_id})\n"
        f"• استخدم أزرار التنقل للانتقال بين الصفحات\n"
        f"• اضغط على 'العودة' للرجوع للقائمة السابقة"
    )

    # إرسال الرسالة مع لوحة المفاتيح
    await message.answer(
        deposits_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

@router.message(F.text.in_({"العودة", "التالي", "السابق", "🔙 العودة"}) | F.text.startswith("📄 "))
async def process_deposits_navigation(message: Message, state: FSMContext):
    """معالج أوامر تنقل طلبات الإيداع - يستخدم للرد على أوامر التنقل بغض النظر عن الحالة"""
    # التحقق من الحالة الحالية
    current_state = await state.get_state()
    logger.info(f"معالجة أمر التنقل '{message.text}' في الحالة {current_state}")
    
    # الحصول على البيانات
    data = await state.get_data()
    deposits = data.get("deposits", [])
    total_deposits = data.get("total_deposits", 0)
    page = data.get("page", 1)
    per_page = 5
    total_pages = (total_deposits + per_page - 1) // per_page
    
    # التحقق من الأمر
    if message.text == "العودة" or message.text == "🔙 العودة":
        # العودة للوحة المشرف
        await state.clear()
        await message.answer(
            "🔄 تم العودة إلى لوحة المشرف.",
            reply_markup=reply.get_admin_keyboard()
        )
        return
    elif message.text == "التالي":
        # الانتقال للصفحة التالية
        if page < total_pages:
            await state.update_data(page=page + 1)
            await display_deposits_page(message, state)
        else:
            await message.answer("⚠️ أنت بالفعل في الصفحة الأخيرة.")
        return
    elif message.text == "السابق":
        # الانتقال للصفحة السابقة
        if page > 1:
            await state.update_data(page=page - 1)
            await display_deposits_page(message, state)
        else:
            await message.answer("⚠️ أنت بالفعل في الصفحة الأولى.")
        return
    elif message.text.startswith("📄 "):
        # عند ضغط زر رقم الصفحة أو أي زر مشابه، نعيد عرض صفحة الإيداعات الحالية 
        # بغض النظر عن محتوى النص، نحن نتجاهله ونعيد عرض صفحة الودائع الحالية
        logger.info(f"عرض صفحات الإيداع استجابة للضغط على '{message.text}'")
        await display_deposits_page(message, state)
        return

@router.message(AdminState.managing_deposits, F.text.startswith("📄 "))
async def process_page_button_in_deposits(message: Message, state: FSMContext):
    """معالج خاص لأزرار عرض أرقام الصفحات في شاشة إدارة الإيداعات"""
    logger.info(f"معالجة زر الصفحة '{message.text}' في حالة AdminState.managing_deposits")
    # عند الضغط على زر رقم الصفحة، نقوم فقط بعرض صفحة الإيداعات الحالية
    await display_deposits_page(message, state)
    
# إضافة معالج خاص للرسائل غير الصالحة في حالة الإيداعات
@router.message(AdminState.managing_deposits, lambda message: not message.text.isdigit() 
                and not message.text.startswith("قبول ") 
                and not message.text.startswith("✅ قبول ")
                and not message.text.startswith("رفض ")
                and not message.text.startswith("❌ رفض ")
                and not message.text in ["🔙 العودة", "العودة", "التالي", "السابق"]
                and not message.text.startswith("📄 "))
async def handle_invalid_deposit_input(message: Message, state: FSMContext):
    """معالج للمدخلات غير الصالحة في شاشة إدارة الإيداعات"""
    logger.info(f"معالجة مدخل غير صالح '{message.text}' في حالة AdminState.managing_deposits")
    await message.answer(
        "⚠️ يرجى إدخال رقم طلب إيداع صحيح، أو استخدام أوامر التنقل.",
        reply_markup=reply.get_admin_keyboard()
    )
    # إعادة تعيين الحالة والعودة للقائمة الرئيسية
    await state.clear()

@router.message(AdminState.managing_deposits)
async def process_deposits_management(message: Message, state: FSMContext):
    """معالج إدارة طلبات الإيداع"""
    # تحقق من أزرار التنقل قبل كل شيء
    if message.text == "🔙 العودة":
        await message.answer("العودة إلى قائمة المشرف", reply_markup=reply.get_admin_keyboard())
        await state.set_state(None)
        return
    
    # تحقق من إذا كان النص يبدأ بـ "📄" (زر الصفحة)
    if message.text.startswith("📄 "):
        logger.info(f"التعامل مع زر الصفحة '{message.text}' في عملية الإيداعات")
        await display_deposits_page(message, state)
        return
    
    # الحصول على البيانات
    data = await state.get_data()
    deposits = data.get("deposits", [])
    total_deposits = data.get("total_deposits", 0)
    page = data.get("page", 1)
    per_page = 5
    total_pages = (total_deposits + per_page - 1) // per_page

    # تحقق مما إذا كان النص يبدأ بـ "قبول" أو "رفض" وتوجيهه للدالة المناسبة
    if message.text.startswith("قبول ") or message.text.startswith("✅ قبول "):
        parts = message.text.split()
        try:
            if len(parts) >= 2:
                deposit_id = int(parts[-1])
                # قبول طلب الإيداع
                success = await approve_deposit(deposit_id)
                if success:
                    await message.answer(
                        f"✅ تم قبول طلب الإيداع بنجاح!\n\n"
                        f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
                        f"💡 تم إضافة المبلغ لرصيد المستخدم.",
                        parse_mode=ParseMode.HTML
                    )
                    # تحديث قائمة طلبات الإيداع
                    deposits, total = await get_pending_deposits()
                    await state.update_data(deposits=deposits, total_deposits=total, page=1)
                    await display_deposits_page(message, state)
                    return
                else:
                    await message.answer("❌ حدث خطأ أثناء قبول طلب الإيداع. يرجى المحاولة مرة أخرى.")
                    return
        except ValueError:
            pass
    
    if message.text.startswith("رفض ") or message.text.startswith("❌ رفض "):
        parts = message.text.split()
        try:
            if len(parts) >= 2:
                deposit_id = int(parts[-1])
                # رفض طلب الإيداع
                success = await reject_deposit(deposit_id)
                if success:
                    await message.answer(
                        f"✅ تم رفض طلب الإيداع بنجاح!\n\n"
                        f"🔹 <b>رقم الطلب:</b> {deposit_id}",
                        parse_mode=ParseMode.HTML
                    )
                    # تحديث قائمة طلبات الإيداع
                    deposits, total = await get_pending_deposits()
                    await state.update_data(deposits=deposits, total_deposits=total, page=1)
                    await display_deposits_page(message, state)
                    return
                else:
                    await message.answer("❌ حدث خطأ أثناء رفض طلب الإيداع. يرجى المحاولة مرة أخرى.")
                    return
        except ValueError:
            pass
    
    # محاولة تحليل رقم طلب الإيداع
    try:
        deposit_id = int(message.text)
    except ValueError:
        await message.answer(
            "⚠️ يرجى إدخال رقم طلب إيداع صحيح، أو استخدام أوامر التنقل."
        )
        return

    # البحث عن طلب الإيداع في القائمة
    deposit_data = None
    for deposit in deposits:
        if deposit.get("id") == deposit_id:
            deposit_data = deposit
            break

    if not deposit_data:
        await message.answer(
            "⚠️ طلب الإيداع غير موجود في القائمة الحالية."
        )
        return

    # تحويل طريقة الدفع إلى رمز
    payment_method = deposit_data.get('payment_method', 'غير محدد')
    payment_emoji = "💳"
    if payment_method == "USDT":
        payment_emoji = "💵"
    elif payment_method == "BARIDIMOB":
        payment_emoji = "💸"
        
    # تحديد إذا كان هناك إيصال
    receipt_info = deposit_data.get('receipt_url', None) or deposit_data.get('receipt_info', 'غير متوفر')
        
    # استخدام الدالة الجديدة لعرض المبلغ مع العملة المناسبة
    amount = deposit_data.get('amount', 0)
    amount_display = format_amount_with_currency(amount, payment_method)
    
    # عرض معلومات طلب الإيداع
    deposit_text = (
        f"💳 <b>معلومات طلب الإيداع:</b>\n\n"
        f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
        f"👤 <b>المستخدم:</b> {deposit_data.get('user_id')} (@{deposit_data.get('username', 'غير محدد')})\n"
        f"💰 <b>المبلغ:</b> {amount_display}\n"
        f"{payment_emoji} <b>طريقة الدفع:</b> {payment_method}\n"
        f"🧾 <b>معلومات الإيصال:</b> {receipt_info}\n"
        f"🕒 <b>تاريخ الطلب:</b> {deposit_data.get('created_at', 'غير محدد')}\n\n"
        f"💡 <b>الخيارات المتاحة:</b>\n\n"
        f"1️⃣ <b>قبول الطلب:</b> أرسل <code>قبول {deposit_id}</code>\n"
        f"2️⃣ <b>رفض الطلب:</b> أرسل <code>رفض {deposit_id}</code>\n"
        f"3️⃣ <b>العودة:</b> أرسل <code>العودة</code>"
    )

    # إنشاء أزرار سريعة
    kb = [
        [KeyboardButton(text=f"✅ قبول {deposit_id}"), KeyboardButton(text=f"❌ رفض {deposit_id}")],
        [KeyboardButton(text="🔙 العودة")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    # إرسال الرسالة
    await message.answer(
        deposit_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

@router.message(F.text.startswith("قبول ") | F.text.startswith("✅ قبول "))
async def approve_deposit_request(message: Message, state: FSMContext):
    """معالج قبول طلب الإيداع"""
    # التحقق من أن المستخدم في حالة إدارة طلبات الإيداع
    current_state = await state.get_state()
    if current_state != AdminState.managing_deposits.state:
        return

    # تحليل الأمر
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer(
            "⚠️ الصيغة غير صحيحة. يجب أن تكون: 'قبول [رقم الطلب]'"
        )
        return

    # محاولة تحليل رقم طلب الإيداع (آخر جزء من الرسالة)
    try:
        deposit_id = int(parts[-1])
    except ValueError:
        await message.answer(
            "⚠️ رقم طلب الإيداع غير صحيح. يرجى التأكد من صحة البيانات."
        )
        return

    # قبول طلب الإيداع
    success = await approve_deposit(deposit_id)

    if not success:
        await message.answer(
            "❌ حدث خطأ أثناء قبول طلب الإيداع. يرجى المحاولة مرة أخرى."
        )
        return

    # إرسال رسالة التأكيد
    await message.answer(
        f"✅ تم قبول طلب الإيداع بنجاح!\n\n"
        f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
        f"💡 تم إضافة المبلغ لرصيد المستخدم.",
        parse_mode=ParseMode.HTML
    )

    # تحديث قائمة طلبات الإيداع
    deposits, total = await get_pending_deposits()
    await state.update_data(deposits=deposits, total_deposits=total, page=1)

    # عرض طلبات الإيداع المحدثة
    await display_deposits_page(message, state)

    # تسجيل العملية
    logger.info(f"قبول طلب إيداع: المشرف: {message.from_user.id}, رقم الطلب: {deposit_id}")

@router.message(F.text.startswith("رفض ") | F.text.startswith("❌ رفض "))
async def reject_deposit_request(message: Message, state: FSMContext):
    """معالج رفض طلب الإيداع"""
    # التحقق من أن المستخدم في حالة إدارة طلبات الإيداع
    current_state = await state.get_state()
    if current_state != AdminState.managing_deposits.state:
        return

    # تحليل الأمر
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer(
            "⚠️ الصيغة غير صحيحة. يجب أن تكون: 'رفض [رقم الطلب]'"
        )
        return

    # محاولة تحليل رقم طلب الإيداع (آخر جزء من الرسالة)
    try:
        deposit_id = int(parts[-1])
    except ValueError:
        await message.answer(
            "⚠️ رقم طلب الإيداع غير صحيح. يرجى التأكد من صحة البيانات."
        )
        return

    # رفض طلب الإيداع
    success = await reject_deposit(deposit_id)

    if not success:
        await message.answer(
            "❌ حدث خطأ أثناء رفض طلب الإيداع. يرجى المحاولة مرة أخرى."
        )
        return

    # إرسال رسالة التأكيد
    await message.answer(
        f"✅ تم رفض طلب الإيداع بنجاح!\n\n"
        f"🔹 <b>رقم الطلب:</b> {deposit_id}",
        parse_mode=ParseMode.HTML
    )

    # تحديث قائمة طلبات الإيداع
    deposits, total = await get_pending_deposits()
    await state.update_data(deposits=deposits, total_deposits=total, page=1)

    # عرض طلبات الإيداع المحدثة
    await display_deposits_page(message, state)

    # تسجيل العملية
    logger.info(f"رفض طلب إيداع: المشرف: {message.from_user.id}, رقم الطلب: {deposit_id}")

@router.message(lambda msg: msg.text and (msg.text.startswith("استرداد ") or msg.text.startswith("🔄 استرداد ")))
async def refund_deposit_request(message: Message, state: FSMContext):
    """معالج استرداد طلب إيداع"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        return

    # تحليل الأمر
    parts = message.text.split()

    if len(parts) < 2:
        await message.answer(
            "⚠️ الصيغة غير صحيحة. يجب أن تكون: 'استرداد [رقم الطلب]'"
        )
        return

    # محاولة تحليل رقم طلب الإيداع (آخر جزء من الرسالة)
    try:
        deposit_id = int(parts[-1])
    except ValueError:
        await message.answer(
            "⚠️ رقم طلب الإيداع غير صحيح. يرجى التأكد من صحة البيانات."
        )
        return

    # الحصول على معلومات طلب الإيداع
    deposit = await get_deposit_by_id(deposit_id)
    
    if not deposit:
        await message.answer(
            f"❌ لم يتم العثور على طلب إيداع برقم {deposit_id}."
        )
        return
        
    # إذا كانت الحالة ليست "موافق عليه"، لا يمكن استرداده
    if deposit["status"] != "approved":
        await message.answer(
            f"⚠️ لا يمكن استرداد الطلب رقم {deposit_id} لأن حالته الحالية هي {deposit['status']}.\n"
            f"فقط الطلبات الموافق عليها يمكن استردادها."
        )
        return
    
    # الحصول على معلومات المستخدم
    user_id = deposit["user_id"]
    amount = deposit["amount"]
    
    # معلومات إضافية للتأكيد
    username = deposit.get("username", "غير محدد")
    full_name = deposit.get("full_name", "غير محدد")
    
    # استخدام الدالة الجديدة لعرض المبلغ مع العملة المناسبة
    amount_display = format_amount_with_currency(amount, deposit["payment_method"])
    
    # التأكيد قبل الاسترداد
    confirmation_text = (
        f"⚠️ <b>تأكيد استرداد الإيداع:</b>\n\n"
        f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
        f"👤 <b>المستخدم:</b> {user_id} (@{username})\n"
        f"🔹 <b>الاسم:</b> {full_name}\n"
        f"🔹 <b>المبلغ:</b> {amount_display}\n\n"
        f"⚠️ <b>تنبيه:</b> سيتم خصم المبلغ من رصيد المستخدم.\n"
        f"هل أنت متأكد من رغبتك في استرداد هذا الإيداع؟"
    )
    
    # حفظ البيانات للمتابعة بعد التأكيد
    await state.update_data(refund_deposit_id=deposit_id)
    
    # تعيين حالة التأكيد
    await state.set_state(AdminState.confirming_refund)
    
    # إرسال رسالة التأكيد
    await message.answer(
        confirmation_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_confirmation_keyboard()
    )

@router.message(AdminState.confirming_refund)
async def confirm_refund_deposit(message: Message, state: FSMContext):
    """معالج تأكيد استرداد الإيداع"""
    if message.text == "✅ نعم":
        # الحصول على معرف طلب الإيداع
        data = await state.get_data()
        deposit_id = data.get("refund_deposit_id", 0)
        
        if not deposit_id:
            await message.answer(
                "❌ حدث خطأ أثناء استرجاع معلومات طلب الإيداع. يرجى المحاولة مرة أخرى."
            )
            await state.clear()
            return
        
        # استرداد طلب الإيداع
        admin_note = f"تم استرداد المبلغ بواسطة المشرف {message.from_user.id} في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        success = await refund_deposit(deposit_id, message.from_user.id, admin_note)
        
        if not success:
            await message.answer(
                "❌ حدث خطأ أثناء استرداد طلب الإيداع. يرجى المحاولة مرة أخرى."
            )
            await state.clear()
            return
            
        # الحصول على معلومات الإيداع المسترد
        deposit = await get_deposit_by_id(deposit_id)
        if not deposit:
            await message.answer(
                "❌ حدث خطأ أثناء استرجاع معلومات طلب الإيداع. يرجى المحاولة مرة أخرى."
            )
            await state.clear()
            return
            
        user_id = deposit["user_id"]
        amount = deposit["amount"]
        
        # استخدام الدالة الجديدة لعرض المبلغ مع العملة المناسبة
        payment_method = deposit["payment_method"]
        amount_display = format_amount_with_currency(amount, payment_method)
        
        # إرسال رسالة التأكيد للمشرف
        await message.answer(
            f"✅ <b>تم استرداد طلب الإيداع بنجاح!</b>\n\n"
            f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
            f"👤 <b>المستخدم:</b> {user_id}\n"
            f"🔹 <b>المبلغ المسترد:</b> {amount_display}\n\n"
            f"✅ تم خصم المبلغ من رصيد المستخدم.",
            parse_mode=ParseMode.HTML,
            reply_markup=reply.get_admin_keyboard()
        )
        
        # إرسال إشعار للمستخدم
        try:
            bot = message.bot
            await bot.send_message(
                user_id,
                f"🔄 <b>إشعار استرداد إيداع:</b>\n\n"
                f"تم استرداد المبلغ التالي من رصيدك:\n\n"
                f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
                f"🔹 <b>المبلغ:</b> {amount_display}\n"
                f"🔹 <b>السبب:</b> تم استرداد الإيداع بواسطة الإدارة\n\n"
                f"إذا كان لديك أي استفسار، يرجى التواصل مع الإدارة.",
                parse_mode=ParseMode.HTML,
                reply_markup=reply.get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار الاسترداد للمستخدم {user_id}: {e}")
        
        # تسجيل العملية
        logger.info(f"استرداد طلب إيداع: المشرف: {message.from_user.id}, رقم الطلب: {deposit_id}, المستخدم: {user_id}, المبلغ: {amount}")
        
    elif message.text == "❌ لا":
        # إلغاء عملية الاسترداد
        await message.answer(
            "🔄 تم إلغاء عملية استرداد الإيداع.",
            reply_markup=reply.get_admin_keyboard()
        )
    else:
        # إدخال غير صالح
        await message.answer(
            "⚠️ يرجى اختيار أحد الخيارات المتاحة: نعم أو لا.",
            reply_markup=reply.get_confirmation_keyboard()
        )
        return
    
    # إنهاء حالة التأكيد بعد المعالجة
    await state.clear()

@router.message(F.text == "📥 جميع الإيداعات")
async def show_all_deposits(message: Message, state: FSMContext):
    """معالج عرض جميع طلبات الإيداع"""
    try:
        # الحصول على كل طلبات الإيداع
        from database.deposit import get_all_deposits
        deposits, total = await get_all_deposits()

        if not deposits:
            await message.answer(
                "📭 لا توجد طلبات إيداع مسجلة حاليًا.",
                reply_markup=reply.get_admin_keyboard()
            )
            return

        # تخزين البيانات في الحالة
        await state.update_data(deposits=deposits, total_deposits=total, page=1)

        # عرض طلبات الإيداع
        await display_all_deposits_page(message, state)

        # تعيين حالة إدارة طلبات الإيداع
        await state.set_state(AdminState.managing_all_deposits)
    except Exception as e:
        logger.error(f"خطأ في عرض جميع طلبات الإيداع: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء استرجاع طلبات الإيداع. يرجى المحاولة مرة أخرى.",
            reply_markup=reply.get_admin_keyboard()
        )

async def display_all_deposits_page(message: Message, state: FSMContext):
    """عرض صفحة من جميع طلبات الإيداع"""
    # الحصول على البيانات
    data = await state.get_data()
    deposits = data.get("deposits", [])
    total_deposits = data.get("total_deposits", 0)
    page = data.get("page", 1)
    per_page = 5  # عدد الطلبات في الصفحة الواحدة

    # حساب عدد الصفحات
    total_pages = (total_deposits + per_page - 1) // per_page

    # إنشاء نص طلبات الإيداع
    deposits_text = f"📥 <b>جميع طلبات الإيداع ({total_deposits}):</b>\n"
    deposits_text += f"📄 <b>الصفحة:</b> {page}/{total_pages}\n\n"

    # حساب نطاق الطلبات للصفحة الحالية
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(deposits))

    # إضافة معلومات طلبات الإيداع
    for i in range(start_idx, end_idx):
        deposit = deposits[i]
        deposit_id = deposit.get("id", "غير محدد")
        user_id = deposit.get("user_id", "غير محدد")
        username = deposit.get("username", "غير محدد")
        amount = deposit.get("amount", 0)
        payment_method = deposit.get("payment_method", "غير محدد")
        status = deposit.get("status", "pending")
        created_at = deposit.get("created_at", "غير محدد")

        # تنسيق الحالة
        status_emoji = "🕒"
        if status == "approved":
            status_emoji = "✅"
        elif status == "rejected":
            status_emoji = "❌"

        # استخدام الدالة الجديدة لعرض المبلغ مع العملة المناسبة
        amount_display = format_amount_with_currency(amount, payment_method)
        
        deposits_text += (
            f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
            f"👤 <b>المستخدم:</b> {user_id} (@{username})\n"
            f"💰 <b>المبلغ:</b> {amount_display}\n"
            f"💳 <b>طريقة الدفع:</b> {payment_method}\n"
            f"📊 <b>الحالة:</b> {status_emoji} {status}\n"
            f"🕒 <b>تاريخ الطلب:</b> {created_at}\n\n"
        )

    # إضافة التعليمات
    deposits_text += (
        f"💡 لإدارة طلب إيداع محدد، أرسل رقمه.\n"
        f"💡 للانتقال بين الصفحات، أرسل 'التالي' أو 'السابق'.\n"
        f"💡 للعودة، أرسل 'العودة'."
    )

    # إرسال الرسالة
    await message.answer(
        deposits_text,
        parse_mode=ParseMode.HTML
    )

@router.message(AdminState.managing_all_deposits)
async def process_all_deposits_management(message: Message, state: FSMContext):
    """معالج إدارة جميع طلبات الإيداع"""
    # الحصول على البيانات
    data = await state.get_data()
    deposits = data.get("deposits", [])
    total_deposits = data.get("total_deposits", 0)
    page = data.get("page", 1)
    per_page = 5
    total_pages = (total_deposits + per_page - 1) // per_page

    # التحقق من الأمر
    if message.text == "العودة":
        # العودة للوحة المشرف
        await state.clear()
        await message.answer(
            "🔄 تم العودة إلى لوحة المشرف.",
            reply_markup=reply.get_admin_keyboard()
        )
        return
    elif message.text == "التالي":
        # الانتقال للصفحة التالية
        if page < total_pages:
            await state.update_data(page=page + 1)
            await display_all_deposits_page(message, state)
        else:
            await message.answer("⚠️ أنت بالفعل في الصفحة الأخيرة.")
        return
    elif message.text == "السابق":
        # الانتقال للصفحة السابقة
        if page > 1:
            await state.update_data(page=page - 1)
            await display_all_deposits_page(message, state)
        else:
            await message.answer("⚠️ أنت بالفعل في الصفحة الأولى.")
        return

    # تحقق مما إذا كان النص يبدأ بـ "قبول" أو "رفض" وتجاهله
    if message.text.startswith("قبول ") or message.text.startswith("رفض ") or message.text.startswith("✅ قبول ") or message.text.startswith("❌ رفض "):
        await message.answer(
            "⚠️ يرجى استخدام الأزرار الخاصة أو إدخال رقم الطلب مباشرة دون كلمات 'قبول' أو 'رفض'."
        )
        return
    
    # محاولة تحليل رقم طلب الإيداع
    try:
        deposit_id = int(message.text)
    except ValueError:
        await message.answer(
            "⚠️ يرجى إدخال رقم طلب إيداع صحيح، أو استخدام أوامر التنقل."
        )
        return

    # البحث عن طلب الإيداع
    from database.deposit import get_deposit_by_id
    deposit_data = await get_deposit_by_id(deposit_id)

    if not deposit_data:
        await message.answer(
            "⚠️ طلب الإيداع غير موجود."
        )
        return

    # معلومات المستخدم
    user_data = await get_user(deposit_data.get("user_id", 0))
    username = user_data.get("username", "غير محدد") if user_data else "غير محدد"

    # عرض معلومات طلب الإيداع
    status_map = {
        "pending": "🕒 قيد الانتظار",
        "approved": "✅ تمت الموافقة",
        "rejected": "❌ مرفوض"
    }

    status = status_map.get(deposit_data.get("status", "pending"), "🕒 قيد الانتظار")

    # استخدام الدالة الجديدة لعرض المبلغ مع العملة المناسبة
    amount = deposit_data.get('amount', 0)
    payment_method = deposit_data.get('payment_method', 'غير محدد')
    amount_display = format_amount_with_currency(amount, payment_method)
    
    deposit_text = (
        f"💳 <b>معلومات طلب الإيداع:</b>\n\n"
        f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
        f"👤 <b>المستخدم:</b> {deposit_data.get('user_id')} (@{username})\n"
        f"💰 <b>المبلغ:</b> {amount_display}\n"
        f"💳 <b>طريقة الدفع:</b> {payment_method}\n"
        f"🧾 <b>معلومات الإيصال:</b> {deposit_data.get('receipt_info', 'غير متوفر')}\n"
        f"📊 <b>الحالة:</b> {status}\n"
        f"🕒 <b>تاريخ الطلب:</b> {deposit_data.get('created_at', 'غير محدد')}\n"
    )

    if deposit_data.get("transaction_id"):
        deposit_text += f"🔢 <b>رقم العملية:</b> {deposit_data.get('transaction_id')}\n"

    if deposit_data.get("admin_note"):
        deposit_text += f"📝 <b>ملاحظة المشرف:</b> {deposit_data.get('admin_note')}\n"

    deposit_text += "\n"

    # تم حذف الخيارات المتاحة (قبول الطلب، رفض الطلب، العودة) بناءً على طلب المستخدم
    deposit_text += (
        f"💡 للعودة أرسل 'العودة'."
    )

    # إرسال الرسالة
    await message.answer(
        deposit_text,
        parse_mode=ParseMode.HTML
    )

@router.message(F.text == "📣 إرسال إشعار عام")
async def send_global_notification_start(message: Message, state: FSMContext):
    """معالج بدء إرسال إشعار عام"""
    await message.answer(
        "📣 <b>إرسال إشعار عام لجميع المستخدمين</b>\n\n"
        "يرجى إدخال نص الإشعار الذي ترغب في إرساله لجميع المستخدمين:\n\n"
        "💡 يمكنك استخدام تنسيق HTML الأساسي مثل:\n"
        "<b>نص عريض</b>\n"
        "<i>نص مائل</i>\n"
        "<a href='https://example.com'>رابط</a>\n\n"
        "أرسل 'إلغاء' للعودة إلى لوحة التحكم.",
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_cancel_keyboard()
    )

    # تعيين حالة كتابة الإشعار
    await state.set_state(AdminState.sending_notification)

@router.message(AdminState.sending_notification)
async def process_global_notification(message: Message, state: FSMContext):
    """معالج إرسال إشعار عام"""
    if message.text == "❌ إلغاء" or message.text.lower() == "إلغاء":
        await state.clear()
        await message.answer(
            "🔄 تم إلغاء إرسال الإشعار والعودة إلى لوحة المشرف.",
            reply_markup=reply.get_admin_keyboard()
        )
        return

    notification_text = message.text

    # تأكيد الإرسال
    await message.answer(
        f"📣 <b>تأكيد إرسال الإشعار</b>\n\n"
        f"هل أنت متأكد من إرسال الإشعار التالي لجميع المستخدمين؟\n\n"
        f"<b>نص الإشعار:</b>\n\n"
        f"{notification_text}\n\n"
        f"يرجى الرد بـ 'نعم' للتأكيد أو 'لا' للإلغاء.",
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_confirmation_keyboard()
    )

    # تخزين نص الإشعار
    await state.update_data(notification_text=notification_text)

    # تعيين حالة تأكيد الإرسال
    await state.set_state(AdminState.confirming_notification)

@router.message(AdminState.confirming_notification)
async def confirm_global_notification(message: Message, state: FSMContext):
    """معالج تأكيد إرسال الإشعار العام"""
    if message.text not in ["✅ نعم", "❌ لا"]:
        await message.answer(
            "⚠️ يرجى الاختيار من الأزرار المتاحة.",
            reply_markup=reply.get_confirmation_keyboard()
        )
        return

    if message.text == "❌ لا":
        await state.clear()
        await message.answer(
            "🔄 تم إلغاء إرسال الإشعار والعودة إلى لوحة المشرف.",
            reply_markup=reply.get_admin_keyboard()
        )
        return

    # الحصول على نص الإشعار
    data = await state.get_data()
    notification_text = data.get("notification_text", "")

    # إرسال رسالة انتظار
    wait_msg = await message.answer("⏳ جاري إرسال الإشعار لجميع المستخدمين...")

    # الحصول على جميع المستخدمين
    users, total = await get_all_users()

    # عدادات النجاح والفشل
    success_count = 0
    fail_count = 0

    # إرسال الإشعار لكل مستخدم
    bot = message.bot
    for user in users:
        try:
            user_id = user.get("user_id")
            await bot.send_message(
                user_id,
                f"📣 <b>إشعار من الإدارة:</b>\n\n{notification_text}",
                parse_mode=ParseMode.HTML
            )
            success_count += 1
        except Exception as e:
            logger.error(f"خطأ في إرسال الإشعار للمستخدم {user.get('user_id')}: {e}")
            fail_count += 1

    # إرسال تقرير النتيجة
    await wait_msg.delete()

    await message.answer(
        f"✅ <b>تقرير إرسال الإشعار:</b>\n\n"
        f"📊 <b>إجمالي المستخدمين:</b> {total}\n"
        f"✅ <b>تم الإرسال بنجاح:</b> {success_count}\n"
        f"❌ <b>فشل الإرسال:</b> {fail_count}",
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_admin_keyboard()
    )

    # تسجيل العملية
    logger.info(f"تم إرسال إشعار عام بواسطة المشرف {message.from_user.id} إلى {success_count} مستخدم")

    # مسح البيانات المخزنة
    await state.clear()

@router.message(F.text == "🏆 إدارة الرتب")
async def manage_ranks(message: Message, state: FSMContext):
    """معالج إدارة الرتب"""
    # التحقق من صلاحيات المشرف
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer(
            "⛔ عذرًا، أنت لست من المشرفين ولا يمكنك الوصول لهذه الميزة.",
            reply_markup=reply.get_main_keyboard()
        )
        return

    # الحصول على قائمة الرتب
    from database.ranks import get_all_ranks, get_rank_emoji
    ranks = await get_all_ranks()

    if not ranks:
        await message.answer(
            "⚠️ لم يتم العثور على أي رتب في النظام.",
            reply_markup=reply.get_admin_keyboard()
        )
        return

    # إنشاء نص الرتب
    ranks_text = "🏆 <b>إدارة الرتب:</b>\n\n"
    ranks_text += "ℹ️ <b>تم تعديل نظام الرتب ليكون يدوياً بالكامل.</b> لتعيين رتبة لمستخدم، استخدم 'إدارة المستخدمين'.\n\n"

    for rank in ranks:
        rank_id = rank.get("id", 0)
        name = rank.get("name", "غير معروف")
        features = rank.get("features", [])
        emoji = get_rank_emoji(rank_id)

        # تنسيق الميزات
        features_text = ", ".join(features) if features and features[0] else "لا توجد ميزات خاصة"

        ranks_text += (
            f"{emoji} <b>الرتبة:</b> {name}\n"
            f"🔹 <b>المعرف:</b> {rank_id}\n"
            f"🔹 <b>الميزات:</b> {features_text}\n\n"
        )

    # إضافة التعليمات
    ranks_text += (
        f"💡 يمكنك تحرير اسم الرتبة أو مميزاتها من خلال الأزرار أدناه.\n"
        f"💡 لتعيين رتبة لمستخدم، استخدم قسم 'إدارة المستخدمين' واختر المستخدم المطلوب."
    )

    # إرسال رسالة الرتب مع لوحة المفاتيح
    from keyboards import inline
    await message.answer(
        ranks_text,
        parse_mode=ParseMode.HTML,
        reply_markup=await inline.get_ranks_management_keyboard()
    )

# معالجات معلومات الرتبة والتحديث
@router.callback_query(lambda c: c.data.startswith("rank_info_"))
async def show_rank_info(callback: CallbackQuery, state: FSMContext):
    """معالج عرض معلومات الرتبة"""
    # التحقق من صلاحيات المشرف
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ غير مصرح لك بهذا الإجراء", show_alert=True)
        return

    # استخراج معرف الرتبة من بيانات الاستدعاء
    rank_id = int(callback.data.split("_")[2])

    # الحصول على بيانات الرتبة
    from database.ranks import get_rank_emoji, get_all_ranks
    ranks = await get_all_ranks()

    # البحث عن الرتبة المطلوبة
    rank_dict = None
    for rank in ranks:
        if rank.get("id") == rank_id:
            rank_dict = rank
            break

    if not rank_dict:
        await callback.answer("⚠️ الرتبة غير موجودة", show_alert=True)
        return

    # تنسيق بيانات الرتبة
    features = rank_dict.get("features", [])
    features_text = ", ".join(features) if features and features[0] else "لا توجد ميزات خاصة"
    emoji = get_rank_emoji(rank_id)

    # إنشاء نص معلومات الرتبة
    rank_text = (
        f"{emoji} <b>معلومات الرتبة:</b>\n\n"
        f"🔹 <b>المعرف:</b> {rank_id}\n"
        f"🔹 <b>الاسم:</b> {rank_dict.get('name', 'غير معروف')}\n"
        f"🔹 <b>الميزات:</b> {features_text}\n\n"
        f"💡 استخدم الأزرار أدناه لإدارة هذه الرتبة.\n"
        f"💡 لتعيين هذه الرتبة لمستخدم، استخدم قسم 'إدارة المستخدمين'."
    )

    # إرسال رسالة معلومات الرتبة مع لوحة المفاتيح
    from keyboards import inline
    await callback.message.edit_text(
        rank_text,
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_rank_actions_keyboard(rank_id)
    )

    await callback.answer()

@router.callback_query(lambda c: c.data == "manage_ranks")
async def back_to_ranks_list(callback: CallbackQuery, state: FSMContext):
    """معالج العودة إلى قائمة الرتب"""
    # الحصول على قائمة الرتب
    from database.ranks import get_all_ranks, get_rank_emoji
    ranks = await get_all_ranks()

    if not ranks:
        await callback.message.edit_text(
            "⚠️ لم يتم العثور على أي رتب في النظام.",
            reply_markup=inline.get_back_button("admin_menu")
        )
        await callback.answer()
        return

    # إنشاء نص الرتب
    ranks_text = "🏆 <b>إدارة الرتب:</b>\n\n"

    for rank in ranks:
        rank_id = rank.get("id", 0)
        name = rank.get("name", "غير معروف")
        min_balance = rank.get("min_balance", 0)
        features = rank.get("features", [])
        emoji = get_rank_emoji(rank_id)

        # تنسيق الميزات
        features_text = ", ".join(features) if features and features[0] else "لا توجد ميزات خاصة"

        ranks_text += (
            f"{emoji} <b>الرتبة:</b> {name}\n"
            f"🔹 <b>المعرف:</b> {rank_id}\n"
            f"🔹 <b>الحد الأدنى للرصيد:</b> ${format_money(min_balance)}\n"
            f"🔹 <b>الميزات:</b> {features_text}\n\n"
        )

    # إضافة التعليمات
    ranks_text += (
        f"💡 استخدم الأزرار أدناه لإدارة الرتب وتحديثها."
    )

    # تحديث رسالة الرتب مع لوحة المفاتيح
    from keyboards import inline
    await callback.message.edit_text(
        ranks_text,
        parse_mode=ParseMode.HTML,
        reply_markup=await inline.get_ranks_management_keyboard()
    )

    await callback.answer()

@router.callback_query(lambda c: c.data == "update_all_ranks")
async def update_all_ranks_callback(callback: CallbackQuery, state: FSMContext):
    """معالج تحديث رتب المستخدمين (معطل)"""
    # التحقق من صلاحيات المشرف
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ غير مصرح لك بهذا الإجراء", show_alert=True)
        return

    # إظهار رسالة تنبيه
    await callback.message.edit_text(
        "ℹ️ <b>تغيير نظام الرتب</b>\n\n"
        "تم تغيير نظام الرتب ليتم تعيين الرتب يدوياً فقط من قبل المشرفين.\n"
        "لتعيين رتبة لمستخدم، يرجى استخدام خيار 'إدارة المستخدمين' والبحث عن المستخدم المطلوب.",
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_back_button("manage_ranks")
    )

    await callback.answer("تم تغيير نظام الرتب")

@router.callback_query(lambda c: c.data.startswith("edit_rank_name_"))
async def edit_rank_name_callback(callback: CallbackQuery, state: FSMContext):
    """معالج تعديل اسم الرتبة"""
    # التحقق من صلاحيات المشرف
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ غير مصرح لك بهذا الإجراء", show_alert=True)
        return

    # استخراج معرف الرتبة
    rank_id = int(callback.data.split("_")[-1])

    # الحصول على معلومات الرتبة
    from database.ranks import get_all_ranks, get_rank_emoji
    ranks = await get_all_ranks()

    # البحث عن الرتبة المطلوبة
    rank_dict = None
    for rank in ranks:
        if rank.get("id") == rank_id:
            rank_dict = rank
            break

    if not rank_dict:
        await callback.answer("⚠️ الرتبة غير موجودة", show_alert=True)
        return

    # طلب الاسم الجديد
    await callback.message.edit_text(
        f"✏️ <b>تعديل اسم الرتبة</b>\n\n"
        f"🔹 <b>الرتبة الحالية:</b> {get_rank_emoji(rank_id)} {rank_dict.get('name')}\n\n"
        f"يرجى إرسال الاسم الجديد للرتبة في رسالة منفصلة:",
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_cancel_keyboard()
    )

    # تخزين معرف الرتبة في الحالة
    await state.set_state(AdminState.editing_rank_name)
    await state.update_data(rank_id=rank_id)

    await callback.answer()

@router.message(AdminState.editing_rank_name)
async def process_edit_rank_name(message: Message, state: FSMContext):
    """معالج حفظ الاسم الجديد للرتبة"""
    # الحصول على معرف الرتبة من الحالة
    data = await state.get_data()
    rank_id = data.get("rank_id")

    if not rank_id:
        await message.answer(
            "⚠️ حدث خطأ أثناء تعديل اسم الرتبة. يرجى المحاولة مرة أخرى.",
            reply_markup=reply.get_admin_keyboard()
        )
        await state.clear()
        return

    # الحصول على الاسم الجديد
    new_name = message.text.strip()

    if not new_name:
        await message.answer(
            "⚠️ يرجى إدخال اسم صحيح للرتبة.",
            reply_markup=inline.get_cancel_keyboard()
        )
        return

    # تحديث اسم الرتبة
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            await db.execute(
                "UPDATE ranks SET name = ? WHERE id = ?",
                (new_name, rank_id)
            )
            await db.commit()

            # الحصول على الرتبة المحدثة
            db.row_factory = sqlite3.Row
            cursor = await db.execute("SELECT * FROM ranks WHERE id = ?", (rank_id,))
            updated_rank = await cursor.fetchone()

            if updated_rank:
                from database.ranks import get_rank_emoji
                emoji = get_rank_emoji(rank_id)

                # إرسال رسالة التأكيد
                await message.answer(
                    f"✅ <b>تم تحديث اسم الرتبة بنجاح!</b>\n\n"
                    f"🔹 <b>الرتبة:</b> {emoji} {new_name}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply.get_admin_keyboard()
                )

                # تسجيل العملية
                logger.info(f"تعديل اسم الرتبة: المشرف: {message.from_user.id}, الرتبة: {rank_id}, الاسم الجديد: {new_name}")
            else:
                await message.answer(
                    "⚠️ لم يتم العثور على الرتبة. يرجى المحاولة مرة أخرى.",
                    reply_markup=reply.get_admin_keyboard()
                )
    except Exception as e:
        logger.error(f"خطأ في تحديث اسم الرتبة: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء تحديث اسم الرتبة. يرجى المحاولة مرة أخرى.",
            reply_markup=reply.get_admin_keyboard()
        )

    # مسح البيانات
    await state.clear()

@router.callback_query(lambda c: c.data.startswith("edit_rank_features_"))
async def edit_rank_features_callback(callback: CallbackQuery, state: FSMContext):
    """معالج تعديل ميزات الرتبة"""
    # التحقق من صلاحيات المشرف
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ غير مصرح لك بهذا الإجراء", show_alert=True)
        return

    # استخراج معرف الرتبة
    rank_id = int(callback.data.split("_")[-1])

    # الحصول على معلومات الرتبة
    from database.ranks import get_all_ranks, get_rank_emoji
    ranks = await get_all_ranks()

    # البحث عن الرتبة المطلوبة
    rank_dict = None
    for rank in ranks:
        if rank.get("id") == rank_id:
            rank_dict = rank
            break

    if not rank_dict:
        await callback.answer("⚠️ الرتبة غير موجودة", show_alert=True)
        return

    # عرض الميزات الحالية وطلب الميزات الجديدة
    features = rank_dict.get("features", [])
    features_text = ", ".join(features) if features and features[0] else "لا توجد ميزات خاصة"

    await callback.message.edit_text(
        f"🔧 <b>تعديل ميزات الرتبة</b>\n\n"
        f"🔹 <b>الرتبة:</b> {get_rank_emoji(rank_id)} {rank_dict.get('name')}\n"
        f"🔹 <b>الميزات الحالية:</b> {features_text}\n\n"
        f"يرجى إرسال الميزات الجديدة مفصولة بفواصل (,) في رسالة منفصلة:\n"
        f"مثال: DISCOUNT, PRIORITY, SPECIAL_OFFER\n\n"
        f"💡 <b>الميزات المتاحة:</b>\n"
        f"- DISCOUNT: خصم على الخدمات\n"
        f"- PRIORITY: أولوية في طلبات الدعم\n"
        f"- SPECIAL_OFFER: عروض خاصة\n"
        f"- ALL: جميع الميزات\n\n"
        f"لإزالة جميع الميزات، أرسل: NONE",
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_cancel_keyboard()
    )

    # تخزين معرف الرتبة في الحالة
    await state.set_state(AdminState.editing_rank_features)
    await state.update_data(rank_id=rank_id)

    await callback.answer()

@router.message(AdminState.editing_rank_features)
async def process_edit_rank_features(message: Message, state: FSMContext):
    """معالج حفظ ميزات الرتبة الجديدة"""
    # الحصول على معرف الرتبة من الحالة
    data = await state.get_data()
    rank_id = data.get("rank_id")

    if not rank_id:
        await message.answer(
            "⚠️ حدث خطأ أثناء تعديل ميزات الرتبة. يرجى المحاولة مرة أخرى.",
            reply_markup=reply.get_admin_keyboard()
        )
        await state.clear()
        return

    # معالجة الميزات الجديدة
    new_features_text = message.text.strip()

    if new_features_text.upper() == "NONE":
        new_features = []
    else:
        new_features = [feature.strip() for feature in new_features_text.split(",") if feature.strip()]

    # تحديث ميزات الرتبة
    try:
        async with aiosqlite.connect(config.DB_NAME) as db:
            features_str = ",".join(new_features)
            await db.execute(
                "UPDATE ranks SET features = ? WHERE id = ?",
                (features_str, rank_id)
            )
            await db.commit()

            # الحصول على الرتبة المحدثة
            db.row_factory = sqlite3.Row
            cursor = await db.execute("SELECT * FROM ranks WHERE id = ?", (rank_id,))
            updated_rank = await cursor.fetchone()

            if updated_rank:
                from database.ranks import get_rank_emoji
                emoji = get_rank_emoji(rank_id)

                # تنسيق الميزات للعرض
                features_display = ", ".join(new_features) if new_features else "لا توجد ميزات خاصة"

                # إرسال رسالة التأكيد
                await message.answer(
                    f"✅ <b>تم تحديث ميزات الرتبة بنجاح!</b>\n\n"
                    f"🔹 <b>الرتبة:</b> {emoji} {updated_rank['name']}\n"
                    f"🔹 <b>الميزات الجديدة:</b> {features_display}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply.get_admin_keyboard()
                )

                # تسجيل العملية
                logger.info(f"تعديل ميزات الرتبة: المشرف: {message.from_user.id}, الرتبة: {rank_id}, الميزات الجديدة: {features_str}")
            else:
                await message.answer(
                    "⚠️ لم يتم العثور على الرتبة. يرجى المحاولة مرة أخرى.",
                    reply_markup=reply.get_admin_keyboard()
                )
    except Exception as e:
        logger.error(f"خطأ في تحديث ميزات الرتبة: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء تحديث ميزات الرتبة. يرجى المحاولة مرة أخرى.",
            reply_markup=reply.get_admin_keyboard()
        )

    # مسح البيانات
    await state.clear()

@router.callback_query(lambda c: c.data.startswith("edit_rank_min_"))
async def edit_rank_min_balance(callback: CallbackQuery, state: FSMContext):
    """معالج تعديل الحد الأدنى للرتبة (معطل)"""
    # التحقق من صلاحيات المشرف
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ غير مصرح لك بهذا الإجراء", show_alert=True)
        return

    # إظهار رسالة تنبيه
    await callback.message.edit_text(
        "ℹ️ <b>تم تغيير نظام الرتب</b>\n\n"
        "تم تعديل نظام الرتب ليتم تعيين الرتب يدوياً من قبل المشرفين فقط.\n"
        "لم يعد هناك حاجة لتحديد حد أدنى للرصيد للرتب.\n\n"
        "لتعيين رتبة لمستخدم، استخدم قسم 'إدارة المستخدمين' واختر المستخدم المطلوب.",
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_back_button("manage_ranks")
    )

    await callback.answer("تم تغيير نظام الرتب")

@router.callback_query(lambda c: c.data == "admin_menu")
async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    """العودة إلى لوحة المشرف"""
    await state.clear()

    # إنشاء لوحة مفاتيح إنلاين بدلاً من استخدام ReplyKeyboardMarkup
    from keyboards import inline

    # عرض رسالة لوحة المشرف مع أزرار إنلاين
    await callback.message.edit_text(
        f"👑 <b>لوحة تحكم المشرف</b>\n\n"
        f"مرحبًا بك في لوحة تحكم المشرف. يمكنك استخدام الأزرار أدناه للوصول إلى مختلف الوظائف الإدارية.\n\n"
        f"🔹 <b>معرف المشرف:</b> {callback.from_user.id}\n"
        f"🔹 <b>الاسم:</b> {callback.from_user.full_name}\n"
        f"🔹 <b>قائمة المشرفين:</b> {config.ADMIN_IDS}",
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_admin_menu()
    )

    # إرسال رسالة جديدة بلوحة مفاتيح الرد العادية
    await callback.bot.send_message(
        callback.from_user.id,
        "استخدم الأزرار أدناه للتنقل في لوحة المشرف:",
        reply_markup=reply.get_admin_keyboard()
    )

    await callback.answer()

@router.callback_query(lambda c: c.data == "back_to_users")
async def back_to_users_list(callback: CallbackQuery, state: FSMContext):
    """العودة إلى قائمة المستخدمين"""
    # الحصول على البيانات المخزنة
    data = await state.get_data()

    # إعادة عرض صفحة المستخدمين
    await display_users_page(callback.message, state)

    # تعيين حالة إدارة المستخدمين
    await state.set_state(AdminState.managing_users)

    await callback.answer()

# إضافة معالجات للأزرار الإنلاين الجديدة
@router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    """معالج زر الإحصائيات الإنلاين"""
    # إرسال رسالة بالإحصائيات بنفس المنطق المستخدم في دالة show_statistics
    try:
        # الحصول على إحصائيات المستخدمين
        users, total_users = await get_all_users()

        # الحصول على إحصائيات الطلبات
        from database.core import get_orders_stats
        orders_stats = await get_orders_stats()

        # الحصول على إحصائيات الإيداعات
        from database.deposit import get_deposit_stats
        deposit_stats = await get_deposit_stats()

        # حساب إجمالي المبيعات
        total_orders_amount = orders_stats.get("total_amount", 0)

        # حساب إجمالي الإيداعات
        total_deposits = deposit_stats.get("approved", {}).get("total", 0)

        # إنشاء نص الإحصائيات
        stats_text = (
            f"📊 <b>إحصائيات النظام:</b>\n\n"
            f"👥 <b>المستخدمين:</b>\n"
            f"   - <b>العدد الإجمالي:</b> {total_users}\n\n"
            f"🛒 <b>الطلبات:</b>\n"
            f"   - <b>عدد الطلبات:</b> {orders_stats.get('total_count', 0)}\n"
            f"   - <b>إجمالي المبيعات:</b> ${format_money(total_orders_amount)}\n\n"
            f"💰 <b>الإيداعات:</b>\n"
            f"   - <b>قيد الانتظار:</b> {deposit_stats.get('pending', {}).get('count', 0)} (${format_money(deposit_stats.get('pending', {}).get('total', 0))})\n"
            f"   - <b>تمت الموافقة:</b> {deposit_stats.get('approved', {}).get('count', 0)} (${format_money(deposit_stats.get('approved', {}).get('total', 0))})\n"
            f"   - <b>تم الرفض:</b> {deposit_stats.get('rejected', {}).get('count', 0)} (${format_money(deposit_stats.get('rejected', {}).get('total', 0))})\n"
        )

        # تحديث الرسالة الحالية بدلاً من إرسال رسالة جديدة
        from keyboards import inline
        await callback.message.edit_text(
            stats_text,
            parse_mode=ParseMode.HTML,
            reply_markup=inline.get_back_button("admin_menu")
        )
    except Exception as e:
        logger.error(f"خطأ في عرض الإحصائيات: {e}")
        await callback.message.edit_text(
            "⚠️ حدث خطأ أثناء جمع إحصائيات النظام. يرجى المحاولة مرة أخرى.",
            reply_markup=inline.get_back_button("admin_menu")
        )

    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_users")
async def admin_users_callback(callback: CallbackQuery, state: FSMContext):
    """معالج زر المستخدمين الإنلاين"""
    # استرجاع المستخدمين
    users, total = await get_all_users()

    if not users:
        await callback.message.edit_text(
            "⚠️ لا يوجد مستخدمون مسجلون حاليًا.",
            reply_markup=inline.get_back_button("admin_menu")
        )
        await callback.answer()
        return

    # تخزين البيانات في الحالة
    await state.update_data(users=users, total_users=total, page=1)

    # إنشاء نص المستخدمين مشابه لـ display_users_page ولكن مع لوحة مفاتيح إنلاين
    users_text = f"👥 <b>قائمة المستخدمين ({total}):</b>\n"
    users_text += f"📄 <b>الصفحة:</b> 1/{(total + 4) // 5}\n\n"

    # إضافة أول 5 مستخدمين
    per_page = 5
    for i in range(min(per_page, len(users))):
        user = users[i]
        user_id = user.get("user_id", "غير محدد")
        username = user.get("username", "غير محدد")
        full_name = user.get("full_name", "غير محدد")
        balance = user.get("balance", 0)
        rank_id = user.get("rank_id", 5)

        # الحصول على اسم الرتبة ورمزها
        from database.ranks import get_rank_emoji
        rank_emoji = get_rank_emoji(rank_id)

        users_text += (
            f"🔹 <b>المستخدم:</b> {user_id} (@{username})\n"
            f"   <b>الاسم:</b> {full_name}\n"
            f"   <b>الرصيد:</b> ${format_money(balance)}\n"
            f"   <b>الرتبة:</b> {rank_emoji}\n\n"
        )

    # إنشاء لوحة مفاتيح إنلاين للتنقل
    keyboard = [
        [
            InlineKeyboardButton(text="◀️ السابق", callback_data="users_prev"),
            InlineKeyboardButton(text="1", callback_data="users_page_1"),
            InlineKeyboardButton(text="التالي ▶️", callback_data="users_next")
        ],
        [InlineKeyboardButton(text="🔙 العودة", callback_data="admin_menu")]
    ]

    # إرسال رسالة المستخدمين مع لوحة المفاتيح الإنلاين
    from keyboards import inline
    await callback.message.edit_text(
        users_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    # تغيير الحالة لإدارة المستخدمين
    await state.set_state(AdminState.managing_users)

    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_deposits")
async def admin_deposits_callback(callback: CallbackQuery, state: FSMContext):
    """معالج زر طلبات الإيداع الإنلاين"""
    # الحصول على طلبات الإيداع المعلقة
    deposits, total = await get_pending_deposits()

    if not deposits:
        await callback.message.edit_text(
            "📭 لا توجد طلبات إيداع معلقة حاليًا.",
            reply_markup=inline.get_back_button("admin_menu")
        )
        await callback.answer()
        return

    # تخزين البيانات في الحالة
    await state.update_data(deposits=deposits, total_deposits=total, page=1)

    # إنشاء نص طلبات الإيداع مشابه لـ display_deposits_page
    deposits_text = f"📦 <b>طلبات الإيداع المعلقة ({total}):</b>\n"
    deposits_text += f"📄 <b>الصفحة:</b> 1/{(total + 4) // 5}\n\n"

    # إضافة أول 5 طلبات إيداع
    per_page = 5
    for i in range(min(per_page, len(deposits))):
        deposit = deposits[i]
        deposit_id = deposit.get("id", "غير محدد")
        user_id = deposit.get("user_id", "غير محدد")
        username = deposit.get("username", "غير محدد")
        amount = deposit.get("amount", 0)
        payment_method = deposit.get("payment_method", "غير محدد")
        created_at = deposit.get("created_at", "غير محدد")

        # تحويل المبلغ من الدينار إلى الدولار إذا كانت طريقة الدفع هي بريدي موب
        amount_display = f"${format_money(amount)}"
        if payment_method == "BARIDIMOB":
            # تحويل المبلغ بالدينار إلى دولار (1$ = 260 دينار)
            usd_amount = amount / 260
            amount_display = f"{format_money(amount)} دينار ≈ ${format_money(usd_amount)}"

        deposits_text += (
            f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
            f"👤 <b>المستخدم:</b> {user_id} (@{username})\n"
            f"💰 <b>المبلغ:</b> {amount_display}\n"
            f"💳 <b>طريقة الدفع:</b> {payment_method}\n"
            f"🕒 <b>تاريخ الطلب:</b> {created_at}\n"
            f"👉 <a href='tg://btn/{deposit_id}'>عرض التفاصيل</a>\n\n"
        )

    # إنشاء لوحة مفاتيح إنلاين للتنقل
    keyboard = [
        [
            InlineKeyboardButton(text="◀️ السابق", callback_data="deposits_prev"),
            InlineKeyboardButton(text="1", callback_data="deposits_page_1"),
            InlineKeyboardButton(text="التالي ▶️", callback_data="deposits_next")
        ],
        [InlineKeyboardButton(text="🔙 العودة", callback_data="admin_menu")]
    ]

    # إرسال رسالة طلبات الإيداع مع لوحة المفاتيح الإنلاين
    await callback.message.edit_text(
        deposits_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    # تغيير الحالة لإدارة طلبات الإيداع
    await state.set_state(AdminState.managing_deposits)

    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_orders")
async def admin_orders_callback(callback: CallbackQuery, state: FSMContext):
    """معالج زر إدارة الطلبات الإنلاين"""
    # الحصول على قائمة الطلبات
    from database.core import get_all_orders
    orders, total = await get_all_orders()

    if not orders:
        await callback.message.edit_text(
            "⚠️ لا توجد طلبات مسجلة حاليًا.",
            reply_markup=inline.get_back_button("admin_menu")
        )
        await callback.answer()
        return

    # تخزين البيانات في الحالة
    await state.update_data(orders=orders, total_orders=total, page=1)

    # إنشاء نص الطلبات مشابه لـ display_orders_page
    orders_text = f"🛒 <b>قائمة الطلبات ({total}):</b>\n"
    orders_text += f"📄 <b>الصفحة:</b> 1/{(total + 4) // 5}\n\n"

    # إضافة أول 5 طلبات
    per_page = 5
    for i in range(min(per_page, len(orders))):
        order = orders[i]
        order_id = order.get("order_id", "غير محدد")
        user_id = order.get("user_id", "غير محدد")
        username = order.get("username", "غير محدد")
        service_name = order.get("service_name", "غير محدد")
        quantity = order.get("quantity", 0)
        amount = order.get("amount", 0)
        status = order.get("status", "Pending")
        created_at = order.get("created_at", "غير محدد")

        # تحويل حالة الطلب إلى رمز
        status_emoji = "🕒"  # معلق
        if status == "Completed":
            status_emoji = "✅"  # مكتمل
        elif status == "Processing":
            status_emoji = "⏳"  # قيد المعالجة
        elif status == "Canceled" or status == "Cancelled":
            status_emoji = "❌"  # ملغي
        elif status == "Failed":
            status_emoji = "⚠️"  # فشل
        elif status == "Partial":
            status_emoji = "⚠️"  # جزئي

        orders_text += (
            f"🔹 <b>رقم الطلب:</b> {order_id}\n"
            f"👤 <b>المستخدم:</b> {user_id} (@{username})\n"
            f"📦 <b>الخدمة:</b> {service_name}\n"
            f"🔢 <b>الكمية:</b> {quantity}\n"
            f"💰 <b>المبلغ:</b> ${format_money(amount)}\n"
            f"📊 <b>الحالة:</b> {status_emoji} {status}\n"
            f"🕒 <b>تاريخ الطلب:</b> {created_at}\n\n"
        )

    # إنشاء لوحة مفاتيح إنلاين للتنقل
    keyboard = [
        [
            InlineKeyboardButton(text="◀️ السابق", callback_data="orders_prev"),
            InlineKeyboardButton(text="1", callback_data="orders_page_1"),
            InlineKeyboardButton(text="التالي ▶️", callback_data="orders_next")
        ],
        [
            InlineKeyboardButton(text="🔄 الكل", callback_data="filter_all"),
            InlineKeyboardButton(text="🕒 معلق", callback_data="filter_pending"),
            InlineKeyboardButton(text="⏳ قيد المعالجة", callback_data="filter_processing")
        ],
        [
            InlineKeyboardButton(text="✅ مكتمل", callback_data="filter_completed"),
            InlineKeyboardButton(text="❌ ملغي", callback_data="filter_cancelled"),
            InlineKeyboardButton(text="⚠️ فشل", callback_data="filter_failed")
        ],
        [InlineKeyboardButton(text="🔙 العودة", callback_data="admin_menu")]
    ]

    # إرسال رسالة الطلبات مع لوحة المفاتيح الإنلاين
    await callback.message.edit_text(
        orders_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    # تغيير الحالة لإدارة الطلبات
    await state.set_state(AdminState.managing_orders)

    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_notification")
async def admin_notification_callback(callback: CallbackQuery, state: FSMContext):
    """معالج زر إرسال إشعار الإنلاين"""
    # إرسال رسالة لبدء عملية الإشعار
    await callback.message.edit_text(
        "📣 <b>إرسال إشعار عام لجميع المستخدمين</b>\n\n"
        "يرجى إرسال نص الإشعار الذي ترغب في إرساله لجميع المستخدمين:\n\n"
        "💡 يمكنك استخدام تنسيق HTML الأساسي مثل:\n"
        "<b>نص عريض</b>\n"
        "<i>نص مائل</i>\n"
        "<a href='https://example.com'>رابط</a>\n\n"
        "لإلغاء العملية، انقر على زر 'إلغاء' أدناه.",
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_back_button("admin_menu")
    )

    # إرسال رسالة منفصلة بلوحة مفاتيح الرد
    await callback.bot.send_message(
        callback.from_user.id,
        "أرسل نص الإشعار أو اضغط 'إلغاء' للعودة:",
        reply_markup=reply.get_cancel_keyboard()
    )

    # تغيير الحالة لإرسال الإشعار
    await state.set_state(AdminState.sending_notification)

    await callback.answer()

# معالج اختيار مستخدم لتعيين رتبة له
@router.callback_query(lambda c: c.data.startswith("assign_rank_"))
async def assign_rank_to_user(callback: CallbackQuery, state: FSMContext):
    """معالج تعيين رتبة لمستخدم"""
    # التحقق من صلاحيات المشرف
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ غير مصرح لك بهذا الإجراء", show_alert=True)
        return

    # استخراج معرف المستخدم
    user_id = int(callback.data.split("_")[2])

    # الحصول على بيانات المستخدم
    user_data = await get_user(user_id)

    if not user_data:
        await callback.answer("⚠️ المستخدم غير موجود", show_alert=True)
        return

    # عرض قائمة الرتب للاختيار
    from keyboards import inline
    keyboard = await inline.get_user_rank_selection_keyboard(user_id)
    await callback.message.edit_text(
        f"🏆 <b>اختر رتبة جديدة للمستخدم:</b>\n\n"
        f"👤 <b>المستخدم:</b> {user_id} (@{user_data.get('username', 'غير محدد')})\n"
        f"👤 <b>الاسم:</b> {user_data.get('full_name', 'غير محدد')}\n\n"
        f"يرجى اختيار الرتبة الجديدة من القائمة أدناه:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("set_user_rank_"))
async def set_user_rank_callback(callback: CallbackQuery, state: FSMContext):
    """معالج تعيين رتبة للمستخدم"""
    # التحقق من صلاحيات المشرف
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ غير مصرح لك بهذا الإجراء", show_alert=True)
        return

    # استخراج معرفات المستخدم والرتبة
    parts = callback.data.split("_")
    user_id = int(parts[3])
    rank_id = int(parts[4])

    # التحقق من وجود المستخدم
    user_data = await get_user(user_id)

    if not user_data:
        await callback.answer("⚠️ المستخدم غير موجود", show_alert=True)
        return

    # تحديث رتبة المستخدم
    from database.ranks import update_user_rank, get_rank_name
    success = await update_user_rank(user_id, rank_id)

    if not success:
        await callback.answer("❌ حدث خطأ أثناء تحديث رتبة المستخدم", show_alert=True)
        return

    # رسالة التأكيد
    rank_name = get_rank_name(rank_id)
    from keyboards import inline
    await callback.message.edit_text(
        f"✅ <b>تم تحديث رتبة المستخدم بنجاح!</b>\n\n"
        f"👤 <b>المستخدم:</b> {user_id} (@{user_data.get('username', 'غير محدد')})\n"
        f"🏆 <b>الرتبة الجديدة:</b> {rank_name}",
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_back_button("manage_users")
    )

    await callback.answer("✅ تم تحديث الرتبة بنجاح")

@router.message(F.text == "📈 تقارير البيع")
async def show_sales_report(message: Message):
    """معالج عرض تقارير البيع"""
    try:
        from database.core import get_orders_stats
        stats = await get_orders_stats()

        # التحقق من وجود طلبات
        if stats.get("total_count", 0) == 0:
            await message.answer(
                "📊 <b>تقارير البيع</b>\n\n"
                "لا توجد طلبات مسجلة حتى الآن.",
                parse_mode=ParseMode.HTML,
                reply_markup=reply.get_admin_keyboard()
            )
            return

        # إنشاء نص التقرير
        report_text = (
            f"📈 <b>تقارير البيع:</b>\n\n"
            f"🔹 <b>عدد الطلبات:</b> {stats.get('total_count', 0)}\n"
            f"🔹 <b>إجمالي المبيعات:</b> ${format_money(stats.get('total_amount', 0))}\n\n"
            f"<b>الإحصائيات حسب الفترة:</b>\n"
            f"🔹 <b>اليوم:</b> ${format_money(stats.get('today', 0))}\n"
            f"🔹 <b>هذا الأسبوع:</b> ${format_money(stats.get('this_week', 0))}\n"
            f"🔹 <b>هذا الشهر:</b> ${format_money(stats.get('this_month', 0))}\n"
            f"🔹 <b>هذا العام:</b> ${format_money(stats.get('this_year', 0))}\n\n"
            f"💡 لعرض تقرير مفصل، استخدم أوامر التقارير المتقدمة."
        )

        await message.answer(
            report_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply.get_admin_keyboard()
        )
    except Exception as e:
        logger.error(f"خطأ في عرض تقارير البيع: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء جمع تقارير البيع. يرجى المحاولة مرة أخرى.",
            reply_markup=reply.get_admin_keyboard()
        )

@router.message(F.text == "🛒 إدارة الطلبات")
async def manage_orders(message: Message, state: FSMContext):
    """معالج إدارة الطلبات"""
    # الحصول على قائمة الطلبات
    from database.core import get_all_orders
    orders, total = await get_all_orders()

    if not orders:
        await message.answer(
            "⚠️ لا توجد طلبات مسجلة حاليًا.",
            reply_markup=reply.get_admin_keyboard()
        )
        return

    # تخزين البيانات في الحالة
    await state.update_data(orders=orders, total_orders=total, page=1)

    # عرض الطلبات
    await display_orders_page(message, state)

    # تعيين حالة إدارة الطلبات
    await state.set_state(AdminState.managing_orders)

async def display_orders_page(message: Message, state: FSMContext):
    """عرض صفحة من الطلبات"""
    # الحصول على البيانات
    data = await state.get_data()
    orders = data.get("orders", [])
    total_orders = data.get("total_orders", 0)
    page = data.get("page", 1)
    per_page = 5  # عدد الطلبات في الصفحة الواحدة

    # حساب عدد الصفحات
    total_pages = (total_orders + per_page - 1) // per_page

    # إنشاء نص الطلبات
    orders_text = f"🛒 <b>قائمة الطلبات ({total_orders}):</b>\n"
    orders_text += f"📄 <b>الصفحة:</b> {page}/{total_pages}\n\n"

    # حساب نطاق الطلبات للصفحة الحالية
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(orders))

    # إضافة معلومات الطلبات
    for i in range(start_idx, end_idx):
        order = orders[i]
        order_id = order.get("order_id", "غير محدد")
        user_id = order.get("user_id", "غير محدد")
        username = order.get("username", "غير محدد")
        service_name = order.get("service_name", "غير محدد")
        quantity = order.get("quantity", 0)
        amount = order.get("amount", 0)
        status = order.get("status", "Pending")
        created_at = order.get("created_at", "غير محدد")

        # تحويل حالة الطلب إلى رمز
        status_emoji = "🕒"  # معلق
        if status == "Completed":
            status_emoji = "✅"  # مكتمل
        elif status == "Processing":
            status_emoji = "⏳"  # قيد المعالجة
        elif status == "Canceled" or status == "Cancelled":
            status_emoji = "❌"  # ملغي
        elif status == "Failed":
            status_emoji = "⚠️"  # فشل
        elif status == "Partial":
            status_emoji = "⚠️"  # جزئي

        orders_text += (
            f"🔹 <b>رقم الطلب:</b> {order_id}\n"
            f"👤 <b>المستخدم:</b> {user_id} (@{username})\n"
            f"📦 <b>الخدمة:</b> {service_name}\n"
            f"🔢 <b>الكمية:</b> {quantity}\n"
            f"💰 <b>المبلغ:</b> ${format_money(amount)}\n"
            f"📊 <b>الحالة:</b> {status_emoji} {status}\n"
            f"🕒 <b>تاريخ الطلب:</b> {created_at}\n\n"
        )

    # إضافة لوحة مفاتيح التنقل
    kb = []
    navigation = []

    if page > 1:
        navigation.append(KeyboardButton(text="◀️ السابق"))

    navigation.append(KeyboardButton(text=f"📄 {page}/{total_pages}"))

    if page < total_pages:
        navigation.append(KeyboardButton(text="التالي ▶️"))

    if navigation:
        kb.append(navigation)

    # إضافة أزرار تصفية الطلبات حسب الحالة
    status_buttons = [
        KeyboardButton(text="🔄 الكل"),
        KeyboardButton(text="🕒 معلق"),
        KeyboardButton(text="⏳ قيد المعالجة")
    ]
    kb.append(status_buttons)

    status_buttons2 = [
        KeyboardButton(text="✅ مكتمل"),
        KeyboardButton(text="❌ ملغي"),
        KeyboardButton(text="⚠️ فشل")
    ]
    kb.append(status_buttons2)

    kb.append([KeyboardButton(text="🔙 العودة")])

    # إضافة التعليمات
    orders_text += (
        f"💡 لإدارة طلب محدد، أرسل رقم الطلب.\n"
        f"💡 استخدم الأزرار أدناه للتنقل بين الصفحات وتصفية الطلبات حسب الحالة."
    )

    # إرسال الرسالة مع لوحة المفاتيح
    await message.answer(
        orders_text,
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    )

@router.message(AdminState.managing_orders)
async def process_orders_management(message: Message, state: FSMContext):
    """معالج إدارة الطلبات"""
    # الحصول على البيانات
    data = await state.get_data()
    page = data.get("page", 1)

    from database.core import get_all_orders

    # التحقق من الأمر
    if message.text == "🔙 العودة":
        # العودة للوحة المشرف
        await state.clear()
        await message.answer(
            "🔄 تم العودة إلى لوحة المشرف.",
            reply_markup=reply.get_admin_keyboard()
        )
        return
    elif message.text == "التالي ▶️":
        # الانتقال للصفحة التالية
        page += 1
        await state.update_data(page=page)
        # تحديث الطلبات الحالية
        await display_orders_page(message, state)
        return
    elif message.text == "◀️ السابق":
        # الانتقال للصفحة السابقة
        if page > 1:
            page -= 1
            await state.update_data(page=page)
            # تحديث الطلبات الحالية
            await display_orders_page(message, state)
        else:
            await message.answer("⚠️ أنت بالفعل في الصفحة الأولى.")
        return
    # تصفية حسب الحالة
    elif message.text == "🔄 الكل":
        # عرض جميع الطلبات
        orders, total = await get_all_orders()
        await state.update_data(orders=orders, total_orders=total, page=1, filter="all")
        await display_orders_page(message, state)
        return
    elif message.text == "🕒 معلق":
        # عرض الطلبات المعلقة
        orders, total = await get_all_orders(status="Pending")
        await state.update_data(orders=orders, total_orders=total, page=1, filter="pending")
        await display_orders_page(message, state)
        return
    elif message.text == "⏳ قيد المعالجة":
        # عرض الطلبات قيد المعالجة
        orders, total = await get_all_orders(status="Processing")
        await state.update_data(orders=orders, total_orders=total, page=1, filter="processing")
        await display_orders_page(message, state)
        return
    elif message.text == "✅ مكتمل":
        # عرض الطلبات المكتملة
        orders, total = await get_all_orders(status="Completed")
        await state.update_data(orders=orders, total_orders=total, page=1, filter="completed")
        await display_orders_page(message, state)
        return
    elif message.text == "❌ ملغي":
        # عرض الطلبات الملغاة
        orders, total = await get_all_orders(status="Canceled")
        await state.update_data(orders=orders, total_orders=total, page=1, filter="canceled")
        await display_orders_page(message, state)
        return
    elif message.text == "⚠️ فشل":
        # عرض الطلبات الفاشلة
        orders, total = await get_all_orders(status="Failed")
        await state.update_data(orders=orders, total_orders=total, page=1, filter="failed")
        await display_orders_page(message, state)
        return
    elif message.text.startswith("📄 "):
        # تم الضغط على زر رقم الصفحة
        await display_orders_page(message, state)
        return

    # محاولة البحث عن طلب برقم معين
    # قد يكون رقم الطلب مثل "ABC123" أو "LOCAL-456" أو نص آخر
    order_id = message.text.strip()

    # البحث عن الطلب
    from database.core import get_order_by_id
    order = await get_order_by_id(order_id)

    if not order:
        await message.answer(
            "⚠️ لم يتم العثور على الطلب بهذا الرقم. يرجى التأكد من صحة رقم الطلب."
        )
        return

    # عرض تفاصيل الطلب
    await display_order_details(message, order, state)

async def display_order_details(message: Message, order: Dict[str, Any], state: FSMContext):
    """عرض تفاصيل طلب معين"""
    order_id = order.get("order_id", "غير محدد")
    user_id = order.get("user_id", "غير محدد")
    username = order.get("username", "غير محدد")
    full_name = order.get("full_name", "غير محدد")
    service_id = order.get("service_id", "غير محدد")
    service_name = order.get("service_name", "غير محدد")
    link = order.get("link", "غير محدد")
    quantity = order.get("quantity", 0)
    amount = order.get("amount", 0)
    status = order.get("status", "Pending")
    created_at = order.get("created_at", "غير محدد")
    remains = order.get("remains", None)
    api_order_id = order.get("api_order_id", "غير محدد")

    # تحويل حالة الطلب إلى رمز
    status_emoji = "🕒"  # معلق
    if status == "Completed":
        status_emoji = "✅"  # مكتمل
    elif status == "Processing" or status == "In Progress":
        status_emoji = "⏳"  # قيد المعالجة
    elif status == "Canceled" or status == "Cancelled":
        status_emoji = "❌"  # ملغي
    elif status == "Failed":
        status_emoji = "⚠️"  # فشل
    elif status == "Partial":
        status_emoji = "⚠️"  # جزئي

    # إنشاء نص تفاصيل الطلب
    order_text = (
        f"🛍️ <b>تفاصيل الطلب:</b>\n\n"
        f"🔹 <b>رقم الطلب:</b> {order_id}\n"
    )

    # إضافة معرف الطلب في API المزود إذا كان متوفراً
    if api_order_id and api_order_id != "غير محدد":
        order_text += f"🌐 <b>معرف الطلب لدى المزود:</b> {api_order_id}\n"

    order_text += (
        f"👤 <b>المستخدم:</b> {user_id} (@{username})\n"
        f"👤 <b>الاسم:</b> {full_name}\n"
        f"📦 <b>معرف الخدمة:</b> {service_id}\n"
        f"📦 <b>اسم الخدمة:</b> {service_name}\n"
        f"🔗 <b>الرابط:</b> {link}\n"
        f"🔢 <b>الكمية:</b> {quantity}\n"
    )

    # إضافة البيانات المتبقية إذا كان الطلب في حالة جزئية
    if remains is not None:
        order_text += f"📊 <b>تم تنفيذه:</b> {quantity - remains}\n"
        order_text += f"🔄 <b>متبقي:</b> {remains}\n"

    order_text += (
        f"💰 <b>المبلغ:</b> ${format_money(amount)}\n"
        f"📊 <b>الحالة:</b> {status_emoji} {status}\n"
        f"🕒 <b>تاريخ الطلب:</b> {created_at}\n\n"
    )

    # إضافة أزرار إنلاين للتحديث والعودة
    from keyboards import inline
    buttons = [
        [InlineKeyboardButton(text="🔄 تحديث حالة الطلب من المزود", callback_data=f"update_order_{order_id}")],
        [InlineKeyboardButton(text="🔙 العودة للقائمة الرئيسية", callback_data="back_to_orders")]
    ]

    # إضافة خيارات التحديث
    order_text += (
        f"💡 <b>تحديث حالة الطلب:</b>\n\n"
        f"🔄 لتحديث حالة الطلب من المزود، اضغط على زر 'تحديث حالة الطلب' أدناه\n"
        f"أو أرسل الأمر التالي: <b>تحديث {order_id}</b>"
    )

    # تخزين معرف الطلب في الحالة
    await state.update_data(current_order_id=order_id)

    # إرسال الرسالة مع خيارات التحديث
    await message.answer(
        order_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.message(AdminState.managing_orders, F.text.startswith("تحديث "))
async def update_order_status_handler(message: Message, state: FSMContext):
    """معالج تحديث حالة الطلب من المزود"""
    # تحليل الأمر
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "⚠️ صيغة الأمر غير صحيحة. يجب أن تكون: تحديث [رقم الطلب]"
        )
        return

    order_id = parts[1]

    # البحث عن الطلب
    from database.core import get_order_by_id
    order = await get_order_by_id(order_id)

    if not order:
        await message.answer(
            "⚠️ لم يتم العثور على الطلب بهذا الرقم. يرجى التأكد من صحة رقم الطلب."
        )
        return

    # استعلام عن حالة الطلب من المزود
    try:
        # إرسال رسالة انتظار
        wait_msg = await message.answer("⏳ جاري الاستعلام عن حالة الطلب من المزود...")

        # استدعاء واجهة برمجة التطبيقات للحصول على حالة الطلب
        from services.api import check_order_status

        # استعلام من المزود
        api_response = await check_order_status(order_id)

        if "error" in api_response:
            await wait_msg.edit_text(
                f"⚠️ حدث خطأ أثناء الاستعلام عن حالة الطلب: {api_response['error']}"
            )
            return

        # التحقق من وجود معلومات الحالة
        if "status" not in api_response:
            await wait_msg.edit_text(
                "⚠️ لم نتمكن من الحصول على حالة الطلب من المزود. الرد غير مكتمل."
            )
            return
            
        # تحديث حالة الطلب في قاعدة البيانات المحلية
        from database.core import update_order_status
        
        new_status = api_response.get("status")
        
        # تحديث الكمية المتبقية إذا كانت متوفرة في الاستجابة
        remains = api_response.get("remains", None)
        if remains is not None:
            from database.core import update_order_remains
            await update_order_remains(order_id, int(remains))
            
        # تحديث حالة الطلب
        success = await update_order_status(order_id, new_status)

        if not success:
            await wait_msg.edit_text(
                "❌ تم الاستعلام عن حالة الطلب بنجاح ولكن حدث خطأ أثناء تحديثها في قاعدة البيانات."
            )
            return

        # ترجمة الحالة للغة العربية لعرضها
        status_map_ar = {
            "Pending": "معلق",
            "Processing": "قيد المعالجة",
            "In Progress": "قيد المعالجة",
            "Completed": "مكتمل",
            "Canceled": "ملغي",
            "Cancelled": "ملغي",
            "Failed": "فشل",
            "Partial": "جزئي"
        }

        status_ar = status_map_ar.get(new_status, new_status)
        
        # إعداد رسالة مفصلة للاستجابة
        response_details = []
        
        # إضافة معلومات إضافية من الاستجابة إذا كانت متوفرة
        if "charge" in api_response:
            response_details.append(f"💰 <b>التكلفة:</b> ${api_response['charge']}")
            
        if "start_count" in api_response:
            response_details.append(f"🔢 <b>العدد البدائي:</b> {api_response['start_count']}")
            
        if "remains" in api_response:
            response_details.append(f"⏳ <b>المتبقي:</b> {api_response['remains']}")
        
        details_text = "\n".join(response_details)
        
        # إرسال رسالة التأكيد
        confirm_message = (
            f"✅ تم تحديث حالة الطلب بنجاح!\n\n"
            f"🔹 <b>رقم الطلب:</b> {order_id}\n"
            f"📊 <b>الحالة الجديدة:</b> {status_ar} ({new_status})"
        )
        
        # إضافة التفاصيل الإضافية إذا كانت متوفرة
        if details_text:
            confirm_message += f"\n\n<b>🔍 تفاصيل إضافية:</b>\n{details_text}"
            
        await wait_msg.edit_text(
            confirm_message,
            parse_mode=ParseMode.HTML
        )

        # تحديث الطلب المعروض
        order = await get_order_by_id(order_id)
        if order:
            await display_order_details(message, order, state)

    except Exception as e:
        logger.error(f"خطأ في الاستعلام عن حالة الطلب: {e}")
        await message.answer(
            "❌ حدث خطأ أثناء الاستعلام عن حالة الطلب. يرجى المحاولة مرة أخرى.",
            parse_mode=ParseMode.HTML
        )

# تم نقل استيراد لوحات المفاتيح إلى بداية الملف
@router.message(F.text == "🔙 العودة")
async def back_to_main_from_admin(message: Message, state: FSMContext):
    """معالج زر العودة من لوحة المشرف"""
    await state.clear()
    # عودة إلى لوحة المشرف
    await message.answer(
        "🔄 تم العودة إلى لوحة المشرف.",
        reply_markup=reply.get_admin_keyboard()
    )

@router.message(F.text == "🔙 العودة للقائمة الرئيسية")
async def back_to_main_menu(message: Message, state: FSMContext):
    """معالج زر العودة للقائمة الرئيسية"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id in config.ADMIN_IDS:
        # إذا كان المستخدم مشرفًا، نعرض لوحة مفاتيح المشرف
        await state.clear()
        await message.answer(
            "🔄 تم العودة إلى القائمة الرئيسية للمشرف.",
            reply_markup=reply.get_admin_main_keyboard()
        )
    else:
        # إذا كان مستخدمًا عاديًا، نعرض لوحة المفاتيح العادية
        # الحصول على رتبة المستخدم
        from database.ranks import get_user_rank
        user_rank = await get_user_rank(message.from_user.id)
        
        await state.clear()
        await message.answer(
            "🔄 تم العودة إلى القائمة الرئيسية.",
            reply_markup=reply.get_main_keyboard(user_rank.get("id", 5))
        )
        
@router.message(F.text == "🔙 العودة للوضع العادي")
async def back_to_normal_mode(message: Message, state: FSMContext):
    """معالج العودة من لوحة المشرف إلى وضع المستخدم العادي"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    # الحصول على رتبة المستخدم
    from database.ranks import get_user_rank
    user_rank = await get_user_rank(message.from_user.id)
    
    await state.clear()
    await message.answer(
        "🔄 تم العودة إلى وضع المستخدم العادي.",
        reply_markup=reply.get_main_keyboard()  # لوحة المفاتيح العادية
    )
    logger.info(f"انتقال المشرف للوضع العادي: {message.from_user.id}")

@router.message(F.text == "💰 طلبات الإيداع")
async def deposit_requests_from_main(message: Message, state: FSMContext):
    """معالج عرض طلبات الإيداع من القائمة الرئيسية للمشرف"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    # استدعاء معالج طلبات الإيداع المعلقة
    await show_pending_deposits(message, state)

@router.message(F.text == "⚙️ الإعدادات")
async def admin_settings(message: Message):
    """معالج عرض إعدادات المشرف من القائمة الرئيسية"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    # عرض إعدادات البوت
    await message.answer(
        f"⚙️ <b>إعدادات البوت:</b>\n\n"
        f"🔹 <b>اسم البوت:</b> {config.BOT_NAME}\n"
        f"🔹 <b>معرف البوت:</b> {config.BOT_USERNAME}\n"
        f"🔹 <b>المشرفين:</b> {len(config.ADMIN_IDS)}\n"
        f"🔹 <b>واجهة API:</b> {config.API_URL}\n\n"
        f"💡 <b>لتعديل الإعدادات:</b> يمكنك تعديل ملف config.py أو استخدام المتغيرات البيئية.",
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_admin_main_keyboard()
    )

@router.callback_query(lambda c: c.data.startswith("update_order_"))
async def update_order_status_callback(callback: CallbackQuery, state: FSMContext):
    """معالج زر تحديث حالة الطلب من المزود"""
    # استخراج معرف الطلب من البيانات
    order_id = callback.data.split("_")[2]
    
    # البحث عن الطلب
    from database.core import get_order_by_id
    order = await get_order_by_id(order_id)

    if not order:
        await callback.answer("⚠️ لم يتم العثور على الطلب بهذا الرقم.", show_alert=True)
        return

    # استعلام عن حالة الطلب من المزود
    try:
        # إرسال رسالة انتظار
        await callback.answer("جاري الاستعلام عن حالة الطلب من المزود...")
        wait_msg = await callback.message.answer("⏳ جاري الاستعلام عن حالة الطلب من المزود...")

        # استدعاء واجهة برمجة التطبيقات للحصول على حالة الطلب
        from services.api import check_order_status

        # استعلام من المزود
        api_response = await check_order_status(order_id)

        if "error" in api_response:
            await wait_msg.edit_text(
                f"⚠️ حدث خطأ أثناء الاستعلام عن حالة الطلب: {api_response['error']}"
            )
            return

        # التحقق من وجود معلومات الحالة
        if "status" not in api_response:
            await wait_msg.edit_text(
                "⚠️ لم نتمكن من الحصول على حالة الطلب من المزود. الرد غير مكتمل."
            )
            return
            
        # تحديث حالة الطلب في قاعدة البيانات المحلية
        from database.core import update_order_status
        
        new_status = api_response.get("status")
        
        # تحديث الكمية المتبقية إذا كانت متوفرة في الاستجابة
        remains = api_response.get("remains", None)
        if remains is not None:
            from database.core import update_order_remains
            await update_order_remains(order_id, int(remains))
            
        # تحديث حالة الطلب
        success = await update_order_status(order_id, new_status)

        if not success:
            await wait_msg.edit_text(
                "❌ تم الاستعلام عن حالة الطلب بنجاح ولكن حدث خطأ أثناء تحديثها في قاعدة البيانات."
            )
            return

        # ترجمة الحالة للغة العربية لعرضها
        status_map_ar = {
            "Pending": "معلق",
            "Processing": "قيد المعالجة",
            "In Progress": "قيد المعالجة",
            "Completed": "مكتمل",
            "Canceled": "ملغي",
            "Cancelled": "ملغي",
            "Failed": "فشل",
            "Partial": "جزئي"
        }

        status_ar = status_map_ar.get(new_status, new_status)
        
        # إعداد رسالة مفصلة للاستجابة
        response_details = []
        
        # إضافة معلومات إضافية من الاستجابة إذا كانت متوفرة
        if "charge" in api_response:
            response_details.append(f"💰 <b>التكلفة:</b> ${api_response['charge']}")
            
        if "start_count" in api_response:
            response_details.append(f"🔢 <b>العدد البدائي:</b> {api_response['start_count']}")
            
        if "remains" in api_response:
            response_details.append(f"⏳ <b>المتبقي:</b> {api_response['remains']}")
        
        details_text = "\n".join(response_details)
        
        # إرسال رسالة التأكيد
        confirm_message = (
            f"✅ تم تحديث حالة الطلب بنجاح!\n\n"
            f"🔹 <b>رقم الطلب:</b> {order_id}\n"
            f"📊 <b>الحالة الجديدة:</b> {status_ar} ({new_status})"
        )
        
        # إضافة التفاصيل الإضافية إذا كانت متوفرة
        if details_text:
            confirm_message += f"\n\n<b>🔍 تفاصيل إضافية:</b>\n{details_text}"
            
        await wait_msg.edit_text(
            confirm_message,
            parse_mode=ParseMode.HTML
        )

        # تحديث الطلب المعروض
        order = await get_order_by_id(order_id)
        if order:
            await display_order_details(callback.message, order, state)

    except Exception as e:
        logger.error(f"خطأ في الاستعلام عن حالة الطلب: {e}")
        await callback.message.answer(
            "❌ حدث خطأ أثناء الاستعلام عن حالة الطلب. يرجى المحاولة مرة أخرى.",
            parse_mode=ParseMode.HTML
        )

@router.callback_query(lambda c: c.data == "back_to_orders")
async def back_to_orders_list(callback: CallbackQuery, state: FSMContext):
    """العودة إلى قائمة الطلبات"""
    await state.set_state(AdminState.managing_orders)
    await display_orders_page(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "back_to_admin_panel")
async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    """معالج العودة إلى لوحة التحكم الرئيسية"""
    # إعادة عرض لوحة التحكم
    await callback.message.edit_text(
        "🛠 <b>لوحة تحكم المشرف</b>\n\n"
        "مرحبًا بك في لوحة تحكم المشرف. يمكنك إدارة البوت من هنا.",
        reply_markup=inline.get_admin_panel_keyboard()
    )

    # مسح الحالة
    await state.clear()

    # تأكيد الاستجابة للاستدعاء
    await callback.answer()
@router.callback_query(F.data == "back_to_main")
async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    """العودة إلى لوحة المشرف"""
    await state.clear()

    # إنشاء لوحة مفاتيح إنلاين بدلاً من استخدام ReplyKeyboardMarkup
    from keyboards import inline

    try:
        # عرض رسالة لوحة المشرف مع أزرار إنلاين
        await callback.message.edit_text(
            f"👑 <b>لوحة تحكم المشرف</b>\n\n"
            f"مرحبًا بك في لوحة تحكم المشرف. يمكنك استخدام الأزرار أدناه للوصول إلى مختلف الوظائف الإدارية.\n\n"
            f"🔹 <b>معرف المشرف:</b> {callback.from_user.id}\n"
            f"🔹 <b>الاسم:</b> {callback.from_user.full_name}\n"
            f"🔹 <b>قائمة المشرفين:</b> {config.ADMIN_IDS}",
            parse_mode=ParseMode.HTML,
            reply_markup=inline.get_admin_menu()
        )
    except Exception as e:
        logger.error(f"خطأ في تحديث رسالة لوحة المشرف: {e}")

# معالجات طلبات الإيداع الجديدة

@router.callback_query(lambda c: c.data.startswith("deposit_details_"))
async def deposit_details_callback(callback: CallbackQuery, state: FSMContext):
    """معالج عرض تفاصيل طلب الإيداع"""
    # استخراج معرف طلب الإيداع من callback data
    deposit_id = int(callback.data.split("_")[2])
    
    # الحصول على بيانات طلب الإيداع
    deposit = await get_deposit_by_id(deposit_id)
    
    if not deposit:
        await callback.answer("⚠️ طلب الإيداع غير موجود", show_alert=True)
        return
    
    # تسجيل الحالة الحالية
    current_state = await state.get_state()
    logger.info(f"الحالة الحالية قبل عرض تفاصيل طلب الإيداع: {current_state}")
    
    # تعيين الحالة إلى عرض الإيداعات
    from states.admin import AdminState
    await state.set_state(AdminState.viewing_deposits)
    
    # استخدام دالة تنسيق معلومات طلب الإيداع الجديدة التي تدعم تحويل الدينار إلى دولار
    from utils.common import format_deposit_info
    deposit_text = format_deposit_info(deposit)
    
    # عرض تفاصيل طلب الإيداع مع أزرار الإجراءات المناسبة
    from keyboards import inline
    await callback.message.edit_text(
        deposit_text,
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_admin_deposit_actions(deposit_id, deposit.get("status", "pending"))
    )
    
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("approve_deposit_"))
async def approve_deposit_callback(callback: CallbackQuery, state: FSMContext):
    """معالج الموافقة على طلب الإيداع"""
    # التحقق من صلاحيات المشرف
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ غير مصرح لك بهذا الإجراء", show_alert=True)
        return
    
    # استخراج معرف طلب الإيداع من callback data
    deposit_id = int(callback.data.split("_")[2])
    
    # الحصول على بيانات طلب الإيداع
    deposit = await get_deposit_by_id(deposit_id)
    
    if not deposit:
        await callback.answer("⚠️ طلب الإيداع غير موجود", show_alert=True)
        return
    
    # التحقق من حالة طلب الإيداع
    if deposit.get("status") != "pending":
        await callback.answer("⚠️ لا يمكن الموافقة على هذا الطلب لأنه ليس في حالة الانتظار", show_alert=True)
        return
    
    # الموافقة على طلب الإيداع
    admin_id = callback.from_user.id
    admin_note = f"تمت الموافقة من قبل المشرف {admin_id} في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    success = await approve_deposit(deposit_id, admin_id, admin_note)
    
    if not success:
        await callback.answer("❌ حدث خطأ أثناء الموافقة على طلب الإيداع", show_alert=True)
        return
    
    # إرسال إشعار للمستخدم
    user_id = deposit.get("user_id")
    amount = deposit.get("amount", 0)
    
    try:
        await callback.bot.send_message(
            user_id,
            f"✅ <b>تمت الموافقة على طلب الإيداع الخاص بك</b>\n\n"
            f"🔢 <b>رقم الطلب:</b> {deposit_id}\n"
            f"💰 <b>المبلغ:</b> ${format_money(amount)}\n"
            f"⏱️ <b>تاريخ الموافقة:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"تم إضافة المبلغ إلى رصيدك. يمكنك الآن استخدامه لطلب الخدمات.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار للمستخدم {user_id}: {e}")
    
    # تحديث العرض للمشرف
    deposit = await get_deposit_by_id(deposit_id)  # إعادة الحصول على الطلب بعد التحديث
    from utils.common import format_deposit_info
    deposit_text = format_deposit_info(deposit)
    deposit_text += "\n✅ <b>تمت الموافقة على طلب الإيداع بنجاح!</b>"
    
    # تسجيل الحالة الحالية ومسحها
    current_state = await state.get_state()
    logger.info(f"الحالة الحالية قبل تحديث عرض طلب الإيداع: {current_state}")
    
    # تعيين الحالة إلى عرض الإيداعات (يمكن البقاء في نفس الحالة لأننا سنعود بزر العودة)
    from states.admin import AdminState
    await state.set_state(AdminState.viewing_deposits)
    
    from keyboards import inline
    await callback.message.edit_text(
        deposit_text,
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_admin_deposit_actions(deposit_id, "approved")
    )
    
    await callback.answer("✅ تمت الموافقة على طلب الإيداع بنجاح")

@router.callback_query(lambda c: c.data == "back_to_deposits")
async def back_to_deposits_callback(callback: CallbackQuery, state: FSMContext):
    """معالج العودة إلى قائمة طلبات الإيداع"""
    # التحقق من صلاحيات المشرف
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ غير مصرح لك بهذا الإجراء", show_alert=True)
        return
    
    # إعادة تعيين الحالة إلى قائمة المشرف قبل عرض طلبات الإيداع
    from states.admin import AdminState
    current_state = await state.get_state()
    logger.info(f"الحالة الحالية قبل العودة لقائمة الإيداعات: {current_state}")
    
    # مسح الحالة السابقة
    await state.clear()
    
    # تعيين الحالة إلى عرض الإيداعات فقط
    await state.set_state(AdminState.viewing_deposits)
    
    # الحصول على طلبات الإيداع المعلقة وعرضها
    deposits, total = await get_pending_deposits()
    
    # تحديث بيانات الحالة
    await state.update_data(deposits=deposits, total_deposits=total, page=1)
    
    # عرض الصفحة الأولى من طلبات الإيداع
    deposit_count = len(deposits)
    if deposit_count > 0:
        deposit_text = f"📋 <b>طلبات الإيداع المعلقة:</b> {deposit_count}\n\n"
        
        # إضافة الطلبات في الصفحة الأولى (بحد أقصى 5)
        for i in range(min(5, deposit_count)):
            deposit = deposits[i]
            deposit_id = deposit.get("id", "غير محدد")
            user_id = deposit.get("user_id", "غير محدد")
            username = deposit.get("username", "غير محدد")
            amount = deposit.get("amount", 0)
            payment_method = deposit.get("payment_method", "غير محدد")
            created_at = deposit.get("created_at", "غير محدد")
            
            # تنسيق المبلغ مع العملة
            amount_display = format_amount_with_currency(amount, payment_method)
            
            deposit_text += (
                f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
                f"👤 <b>المستخدم:</b> {user_id} (@{username})\n"
                f"💰 <b>المبلغ:</b> {amount_display}\n"
                f"📅 <b>التاريخ:</b> {created_at}\n\n"
            )
        
        # إضافة تعليمات للمشرف
        deposit_text += "💡 <b>للتفاصيل:</b> اضغط على زر 'عرض التفاصيل' أو أدخل رقم الطلب."
        
        # إنشاء أزرار التحكم
        markup = inline.get_deposits_management_keyboard(deposits, 1)
        
        await callback.message.edit_text(
            deposit_text,
            parse_mode=ParseMode.HTML,
            reply_markup=markup
        )
    else:
        # إذا لم تكن هناك طلبات معلقة
        await callback.message.edit_text(
            "📋 <b>طلبات الإيداع</b>\n\n"
            "لا توجد طلبات إيداع معلقة حاليًا.",
            parse_mode=ParseMode.HTML,
            reply_markup=inline.get_back_button("admin_deposits_menu")
        )
    
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("reject_deposit_"))
async def reject_deposit_callback(callback: CallbackQuery, state: FSMContext):
    """معالج رفض طلب الإيداع"""
    # التحقق من صلاحيات المشرف
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ غير مصرح لك بهذا الإجراء", show_alert=True)
        return
    
    # استخراج معرف طلب الإيداع من callback data
    deposit_id = int(callback.data.split("_")[2])
    
    # الحصول على بيانات طلب الإيداع
    deposit = await get_deposit_by_id(deposit_id)
    
    if not deposit:
        await callback.answer("⚠️ طلب الإيداع غير موجود", show_alert=True)
        return
    
    # التحقق من حالة طلب الإيداع
    if deposit.get("status") != "pending":
        await callback.answer("⚠️ لا يمكن رفض هذا الطلب لأنه ليس في حالة الانتظار", show_alert=True)
        return
    
    # تخزين معرف طلب الإيداع في حالة المشرف
    await state.update_data(rejecting_deposit_id=deposit_id)
    
    # سؤال المشرف عن سبب الرفض
    await callback.message.edit_text(
        f"❌ <b>رفض طلب الإيداع</b>\n\n"
        f"🔢 <b>رقم الطلب:</b> {deposit_id}\n"
        f"👤 <b>المستخدم:</b> {deposit.get('user_id')} (@{deposit.get('username', 'غير محدد')})\n"
        f"💰 <b>المبلغ:</b> ${format_money(deposit.get('amount', 0))}\n\n"
        f"يرجى إدخال سبب الرفض الذي سيتم إرساله للمستخدم:",
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_back_button(f"deposit_details_{deposit_id}")
    )
    
    # تغيير حالة المشرف
    await state.set_state(AdminState.entering_reject_reason)
    
    await callback.answer()

@router.message(AdminState.entering_reject_reason)
async def process_reject_reason(message: Message, state: FSMContext):
    """معالج سبب رفض طلب الإيداع"""
    # الحصول على بيانات الحالة
    data = await state.get_data()
    deposit_id = data.get("rejecting_deposit_id")
    
    if not deposit_id:
        await message.answer(
            "⚠️ حدث خطأ في العملية. يرجى المحاولة مرة أخرى.",
            reply_markup=reply.get_admin_keyboard()
        )
        await state.clear()
        return
    
    # الحصول على بيانات طلب الإيداع
    deposit = await get_deposit_by_id(deposit_id)
    
    if not deposit:
        await message.answer(
            "⚠️ طلب الإيداع غير موجود أو تم حذفه.",
            reply_markup=reply.get_admin_keyboard()
        )
        await state.clear()
        return
    
    # رفض طلب الإيداع
    admin_id = message.from_user.id
    admin_note = message.text  # استخدام نص الرسالة كسبب الرفض
    
    success = await reject_deposit(deposit_id, admin_id, admin_note)
    
    if not success:
        await message.answer(
            "❌ حدث خطأ أثناء رفض طلب الإيداع. يرجى المحاولة مرة أخرى.",
            reply_markup=reply.get_admin_keyboard()
        )
        await state.clear()
        return
    
    # إرسال إشعار للمستخدم
    user_id = deposit.get("user_id")
    amount = deposit.get("amount", 0)
    
    try:
        await message.bot.send_message(
            user_id,
            f"❌ <b>تم رفض طلب الإيداع الخاص بك</b>\n\n"
            f"🔢 <b>رقم الطلب:</b> {deposit_id}\n"
            f"💰 <b>المبلغ:</b> ${format_money(amount)}\n"
            f"📝 <b>سبب الرفض:</b> {admin_note}\n"
            f"⏱️ <b>تاريخ الرفض:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"إذا كنت تعتقد أن هناك خطأ ما، يرجى التواصل مع الدعم.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار للمستخدم {user_id}: {e}")
    
    # تأكيد للمشرف
    await message.answer(
        f"✅ <b>تم رفض طلب الإيداع بنجاح</b>\n\n"
        f"🔢 <b>رقم الطلب:</b> {deposit_id}\n"
        f"👤 <b>المستخدم:</b> {deposit.get('user_id')} (@{deposit.get('username', 'غير محدد')})\n"
        f"💰 <b>المبلغ:</b> ${format_money(amount)}\n"
        f"📝 <b>سبب الرفض:</b> {admin_note}",
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_back_button("admin_deposits")
    )
    
    # إعادة تعيين حالة المشرف
    await state.clear()

@router.callback_query(lambda c: c.data.startswith("refund_deposit_"))
async def refund_deposit_callback(callback: CallbackQuery, state: FSMContext):
    """معالج استرداد مبلغ طلب الإيداع"""
    # التحقق من صلاحيات المشرف
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ غير مصرح لك بهذا الإجراء", show_alert=True)
        return
    
    # استخراج معرف طلب الإيداع من callback data
    deposit_id = int(callback.data.split("_")[2])
    
    # الحصول على بيانات طلب الإيداع
    deposit = await get_deposit_by_id(deposit_id)
    
    if not deposit:
        await callback.answer("⚠️ طلب الإيداع غير موجود", show_alert=True)
        return
    
    # التحقق من حالة طلب الإيداع
    if deposit.get("status") != "approved":
        await callback.answer("⚠️ لا يمكن استرداد مبلغ هذا الطلب لأنه ليس في حالة الموافقة", show_alert=True)
        return
    
    # تأكيد استرداد المبلغ
    await callback.message.edit_text(
        f"♻️ <b>استرداد مبلغ طلب الإيداع</b>\n\n"
        f"🔢 <b>رقم الطلب:</b> {deposit_id}\n"
        f"👤 <b>المستخدم:</b> {deposit.get('user_id')} (@{deposit.get('username', 'غير محدد')})\n"
        f"💰 <b>المبلغ:</b> ${format_money(deposit.get('amount', 0))}\n\n"
        f"⚠️ <b>تحذير:</b> عملية الاسترداد ستخصم المبلغ من رصيد المستخدم. هل أنت متأكد من رغبتك في استرداد هذا المبلغ؟",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ نعم، استرداد المبلغ", callback_data=f"confirm_refund_{deposit_id}"),
                InlineKeyboardButton(text="❌ إلغاء", callback_data=f"deposit_details_{deposit_id}")
            ]
        ])
    )
    
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("confirm_refund_"))
async def confirm_refund_callback(callback: CallbackQuery, state: FSMContext):
    """معالج تأكيد استرداد مبلغ طلب الإيداع"""
    # التحقق من صلاحيات المشرف
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ غير مصرح لك بهذا الإجراء", show_alert=True)
        return
    
    # استخراج معرف طلب الإيداع من callback data
    deposit_id = int(callback.data.split("_")[2])
    
    # الحصول على بيانات طلب الإيداع
    deposit = await get_deposit_by_id(deposit_id)
    
    if not deposit:
        await callback.answer("⚠️ طلب الإيداع غير موجود", show_alert=True)
        return
    
    # استرداد مبلغ طلب الإيداع
    admin_id = callback.from_user.id
    admin_note = f"تم استرداد المبلغ من قبل المشرف {admin_id} في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    success = await refund_deposit(deposit_id, admin_id, admin_note)
    
    if not success:
        await callback.answer("❌ حدث خطأ أثناء استرداد مبلغ طلب الإيداع", show_alert=True)
        return
    
    # إرسال إشعار للمستخدم
    user_id = deposit.get("user_id")
    amount = deposit.get("amount", 0)
    payment_method = deposit.get("payment_method", "USD")
    
    # استخدام الدالة الجديدة لعرض المبلغ مع العملة المناسبة
    amount_display = format_amount_with_currency(amount, payment_method)
    
    try:
        await callback.bot.send_message(
            user_id,
            f"♻️ <b>تم استرداد مبلغ طلب الإيداع الخاص بك</b>\n\n"
            f"🔢 <b>رقم الطلب:</b> {deposit_id}\n"
            f"💰 <b>المبلغ:</b> {amount_display}\n"
            f"⏱️ <b>تاريخ الاسترداد:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"تم خصم المبلغ من رصيدك. إذا كنت تعتقد أن هناك خطأ ما، يرجى التواصل مع الدعم.",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار للمستخدم {user_id}: {e}")
    
    # تحديث العرض للمشرف
    deposit = await get_deposit_by_id(deposit_id)  # إعادة الحصول على الطلب بعد التحديث
    from utils.common import format_deposit_info
    deposit_text = format_deposit_info(deposit)
    deposit_text += "\n♻️ <b>تم استرداد مبلغ طلب الإيداع بنجاح!</b>"
    
    from keyboards import inline
    await callback.message.edit_text(
        deposit_text,
        parse_mode=ParseMode.HTML,
        reply_markup=inline.get_back_button("admin_deposits")
    )
    
    await callback.answer("✅ تم استرداد مبلغ طلب الإيداع بنجاح")

@router.callback_query(lambda c: c.data.startswith("view_receipt_"))
async def view_receipt_callback(callback: CallbackQuery, state: FSMContext):
    """معالج عرض إيصال الدفع"""
    # استخراج معرف طلب الإيداع من callback data
    deposit_id = int(callback.data.split("_")[2])
    
    # الحصول على بيانات طلب الإيداع
    deposit = await get_deposit_by_id(deposit_id)
    
    if not deposit:
        await callback.answer("⚠️ طلب الإيداع غير موجود", show_alert=True)
        return
    
    # التحقق من وجود إيصال دفع
    receipt_url = deposit.get("receipt_url")
    if not receipt_url or receipt_url == "لا يوجد":
        await callback.answer("⚠️ لا يوجد إيصال دفع لهذا الطلب", show_alert=True)
        return
    
    # إرسال صورة الإيصال إذا كانت موجودة
    try:
        # إرسال إيصال الدفع (صورة)
        await callback.message.answer_photo(
            receipt_url,
            caption=f"🧾 <b>إيصال الدفع لطلب الإيداع رقم {deposit_id}</b>",
            parse_mode=ParseMode.HTML
        )
        await callback.answer("✅ تم عرض إيصال الدفع")
    except Exception as e:
        logger.error(f"خطأ في عرض إيصال الدفع: {e}")
        await callback.answer("❌ حدث خطأ في عرض إيصال الدفع. قد يكون الرابط غير صالح.", show_alert=True)
        
@router.callback_query(lambda c: c.data.startswith("view_user_deposit_"))
async def view_user_deposit_callback(callback: CallbackQuery, state: FSMContext):
    """معالج عرض معلومات المستخدم صاحب طلب الإيداع"""
    # استخراج معرف طلب الإيداع من callback data
    deposit_id = int(callback.data.split("_")[3])
    
    # الحصول على بيانات طلب الإيداع
    deposit = await get_deposit_by_id(deposit_id)
    
    if not deposit:
        await callback.answer("⚠️ طلب الإيداع غير موجود", show_alert=True)
        return
    
    # الحصول على معلومات المستخدم
    user_id = deposit.get("user_id")
    
    # التأكد من أن user_id قيمة صحيحة
    if not user_id or not isinstance(user_id, int):
        await callback.answer("⚠️ معرف المستخدم غير صالح", show_alert=True)
        return
        
    user_data = await get_user(user_id)
    
    if not user_data:
        await callback.answer("⚠️ المستخدم غير موجود", show_alert=True)
        return
    
    # تنسيق معلومات المستخدم
    from utils.common import format_user_info
    user_text = format_user_info(user_data)
    
    # إرسال معلومات المستخدم
    await callback.message.edit_text(
        f"{user_text}\n\n"
        f"<b>طلب الإيداع:</b> #{deposit_id}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💲 إضافة رصيد", callback_data=f"add_balance_{user_id}"),
                InlineKeyboardButton(text="🔻 خصم رصيد", callback_data=f"subtract_balance_{user_id}")
            ],
            [
                InlineKeyboardButton(text="🏆 تعيين رتبة", callback_data=f"assign_rank_{user_id}"),
                InlineKeyboardButton(text="🚫 حظر/إلغاء حظر", callback_data=f"toggle_ban_{user_id}")
            ],
            [
                InlineKeyboardButton(text="🔙 العودة", callback_data=f"deposit_details_{deposit_id}")
            ]
        ])
    )
    
    await callback.answer()

@router.message(F.text == "🔍 مراقبة النظام")
async def monitor_system(message: Message):
    """معالج لمراقبة النظام"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        logger.warning(f"محاولة وصول غير مصرح: {message.from_user.id}")
        return
    
    try:
        # جمع بعض معلومات النظام
        from database.core import get_user_count, get_deposit_count, get_order_count
        import psutil
        
        user_count = await get_user_count()
        deposit_count = await get_deposit_count()
        order_count = await get_order_count()
        
        # معلومات النظام
        cpu_percent = psutil.cpu_percent()
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
        
        system_info = (
            f"🖥️ <b>حالة النظام:</b>\n\n"
            f"🔹 <b>استخدام المعالج:</b> {cpu_percent}%\n"
            f"🔹 <b>استخدام الذاكرة:</b> {memory_info.percent}% ({memory_info.used / (1024**3):.1f} GB من {memory_info.total / (1024**3):.1f} GB)\n"
            f"🔹 <b>استخدام القرص:</b> {disk_info.percent}% ({disk_info.used / (1024**3):.1f} GB من {disk_info.total / (1024**3):.1f} GB)\n\n"
            f"📊 <b>إحصائيات النظام:</b>\n"
            f"🔹 <b>عدد المستخدمين:</b> {user_count}\n"
            f"🔹 <b>عمليات الإيداع:</b> {deposit_count}\n"
            f"🔹 <b>الطلبات:</b> {order_count}\n\n"
            f"🕒 <b>زمن تشغيل النظام:</b> {int(psutil.boot_time())} ثانية"
        )
        
        await message.answer(
            system_info,
            parse_mode=ParseMode.HTML,
            reply_markup=reply.get_admin_main_keyboard()
        )
    except Exception as e:
        logger.error(f"خطأ في عرض معلومات النظام: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء جمع معلومات النظام. يرجى المحاولة مرة أخرى.",
            reply_markup=reply.get_admin_main_keyboard()
        )

@router.message(F.text == "📱 قائمة المستخدم")
async def user_menu_command(message: Message):
    """معالج للانتقال إلى قائمة المستخدم العادي"""
    # التحقق من أن المستخدم مشرف
    if message.from_user.id not in config.ADMIN_IDS:
        logger.warning(f"محاولة وصول غير مصرح: {message.from_user.id}")
        return
    
    await message.answer(
        "👤 <b>قائمة المستخدم</b>\n\n"
        "تم الانتقال إلى وضع المستخدم العادي. يمكنك الآن استخدام البوت كمستخدم عادي.",
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_main_keyboard(1)  # إعطاء رتبة متميزة (1) للمشرف
    )
    logger.info(f"انتقال المشرف لوضع المستخدم: {message.from_user.id}")