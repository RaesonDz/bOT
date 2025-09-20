"""
معالجات المستخدم العادي
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from states.order import OrderState, DepositState, UserState

from database.core import get_user, update_user_balance
from database.deposit import create_deposit_request, update_deposit_receipt
from utils.common import format_money, validate_number
import config
from services.api import get_services, organize_services_by_category, add_order, check_order_status, get_user_orders

# إنشاء مسجل
logger = logging.getLogger("smm_bot")

# إنشاء موجه
router = Router(name="user")

# حدود الطلب
MIN_ORDER = config.MIN_ORDER

@router.message(CommandStart())
async def cmd_start(message: Message):
    """معالج أمر البدء"""
    # الحصول على معلومات المستخدم
    user_id = message.from_user.id
    username = message.from_user.username or "غير محدد"
    full_name = message.from_user.full_name or "غير محدد"

    # التحقق إذا كان المستخدم مشرفًا
    is_admin = user_id in config.ADMIN_IDS
    if is_admin:
        logger.info(f"بدء تشغيل البوت بواسطة مشرف: {user_id}, {username}")

    try:
        # التحقق من وجود المستخدم وإنشائه إذا لم يكن موجودًا
        user_data = await get_user(user_id)
        if not user_data:
            from database.core import create_user
            await create_user(user_id, username, full_name)
            logger.info(f"تم إنشاء مستخدم جديد: {user_id}, {username}, {full_name}")
    except Exception as e:
        logger.error(f"خطأ في إنشاء المستخدم: {e}")

    # الحصول على رتبة المستخدم
    from database.ranks import get_user_rank, get_rank_emoji
    user_rank = await get_user_rank(user_id)
    rank_name = user_rank.get("name", "برونزي")
    rank_emoji = get_rank_emoji(user_rank.get("id", 5))

    # رسالة الترحيب
    welcome_message = f"👋 مرحبًا {full_name}!\n\n"

    if is_admin:
        welcome_message += "✅ <b>تم التعرف عليك كمشرف في النظام.</b>\n\n"
    else:
        welcome_message += f"{rank_emoji} <b>رتبتك الحالية:</b> {rank_name}\n\n"

    welcome_message += f"أنا بوت خدمات السوشيال ميديا، يمكنك من خلالي طلب خدمات متنوعة مثل المتابعين والإعجابات والمشاهدات وغيرها.\n\n"
    welcome_message += f"استخدم الأزرار أدناه للتنقل بين خدمات البوت:"

    # إرسال لوحة المفاتيح المناسبة حسب نوع المستخدم
    keyboard = reply.get_admin_main_keyboard() if is_admin else reply.get_main_keyboard()

    await message.answer(
        welcome_message,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

@router.message(F.text == "🔄 طلب جديد")
async def new_order(message: Message, state: FSMContext):
    """معالج طلب جديد"""
    # الحصول على الخدمات من API
    services = await get_services()

    if not services:
        await message.answer("⚠️ عذرًا، لا يمكن الحصول على قائمة الخدمات حاليًا. يرجى المحاولة لاحقًا.")
        return

    # تنظيم الخدمات حسب الفئة
    categories = organize_services_by_category(services)

    # تخزين الخدمات في حالة المستخدم للاستخدام لاحقًا
    await state.update_data(categories=categories)

    # إنشاء قائمة بأسماء الفئات
    category_names = list(categories.keys())

    # عرض الفئات للمستخدم
    await message.answer(
        "🔍 يرجى اختيار الفئة المطلوبة:",
        reply_markup=reply.get_categories_keyboard([(i, name) for i, name in enumerate(category_names)])
    )

    # تعيين حالة اختيار الفئة
    await state.set_state(OrderState.selecting_category)

@router.message(OrderState.selecting_category)
async def process_category_selection(message: Message, state: FSMContext):
    """معالج اختيار الفئة"""
    # الحصول على البيانات المخزنة
    data = await state.get_data()
    categories = data.get("categories", {})
    category_names = list(categories.keys())

    # التحقق من صحة اختيار الفئة
    if message.text == "🔙 العودة":
        # العودة للقائمة الرئيسية
        await state.clear()
        await message.answer(
            "🔄 تم العودة إلى القائمة الرئيسية.",
            reply_markup=reply.get_main_keyboard()
        )
        return

    # البحث عن الفئة المختارة
    selected_category = None
    for name in category_names:
        if message.text == name:
            selected_category = name
            break

    if not selected_category:
        await message.answer(
            "⚠️ يرجى اختيار فئة صحيحة من القائمة.",
            reply_markup=reply.get_categories_keyboard([(i, name) for i, name in enumerate(category_names)])
        )
        return

    # تخزين الفئة المختارة
    await state.update_data(selected_category=selected_category)

    # الحصول على خدمات الفئة المختارة
    services = categories.get(selected_category, [])

    if not services:
        await message.answer(
            "⚠️ لا توجد خدمات متاحة في هذه الفئة حاليًا.",
            reply_markup=reply.get_main_keyboard()
        )
        await state.clear()
        return

    # عرض عنوان الخدمات
    services_text = f"📋 الخدمات المتاحة في فئة {selected_category}:\n\n"
    services_text += "يرجى اختيار الخدمة المطلوبة من القائمة:"

    # عرض الخدمات كأزرار
    await message.answer(
        services_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_services_keyboard(services)
    )

    # تعيين حالة اختيار الخدمة
    await state.set_state(OrderState.selecting_service)

@router.message(OrderState.selecting_service)
async def process_service_selection(message: Message, state: FSMContext):
    """معالج اختيار الخدمة"""
    # إلغاء الطلب أو العودة
    if message.text == "❌ إلغاء" or message.text == "🔙 العودة":
        # إذا كان العودة، نعود للفئات، وإلا نعود للقائمة الرئيسية
        if message.text == "🔙 العودة":
            # العودة لاختيار الفئات
            # الحصول على الخدمات من API
            services = await get_services()

            if not services:
                await message.answer("⚠️ عذرًا، لا يمكن الحصول على قائمة الخدمات حاليًا. يرجى المحاولة لاحقًا.")
                await state.clear()
                return

            # تنظيم الخدمات حسب الفئة
            categories = organize_services_by_category(services)

            # تخزين الخدمات في حالة المستخدم للاستخدام لاحقًا
            await state.update_data(categories=categories)

            # إنشاء قائمة بأسماء الفئات
            category_names = list(categories.keys())

            # عرض الفئات للمستخدم
            await message.answer(
                "🔍 يرجى اختيار الفئة المطلوبة:",
                reply_markup=reply.get_categories_keyboard([(i, name) for i, name in enumerate(category_names)])
            )

            # تعيين حالة اختيار الفئة
            await state.set_state(OrderState.selecting_category)
        else:
            # إلغاء الطلب كليًا
            await state.clear()
            await message.answer(
                "🔄 تم إلغاء الطلب والعودة إلى القائمة الرئيسية.",
                reply_markup=reply.get_main_keyboard()
            )
        return

    # الحصول على البيانات المخزنة
    data = await state.get_data()
    categories = data.get("categories", {})
    selected_category = data.get("selected_category", "")

    # البحث عن الخدمة المختارة
    services = categories.get(selected_category, [])
    selected_service = None

    # استخراج رقم الخدمة من النص المحدد باستخدام تعبير منتظم
    import re
    service_id = None

    # البحث عن رقم بعده نقطة في بداية النص (مثل "123. اسم الخدمة")
    match = re.match(r'(\d+)\.', message.text)
    if match:
        service_id = int(match.group(1))

    # البحث عن الخدمة بناءً على الرقم
    if service_id:
        for service in services:
            if service.get("service") == service_id:
                selected_service = service
                break

    # إذا لم نجد حسب الرقم، نبحث في النص الكامل
    if not selected_service:
        # نبحث عن كل النص بنفس الصيغة
        for service in services:
            service_id = service.get("service", "غير محدد")
            name = service.get("name", "غير محدد")
            price = service.get("rate", "غير محدد")

            # تحديد نوع التسعير للمطابقة مع نص الزر
            try:
                max_order = int(service.get("max", 0)) if isinstance(service.get("max"), str) else service.get("max", 0)
                price_format = "للباقة" if max_order == 1 else "لكل 1000"
            except (ValueError, TypeError):
                price_format = "لكل 1000"

            # نفس الصيغة المستخدمة للزر مع نوع التسعير
            button_text = f"{service_id}. {name} ({price}$ {price_format})"

            if message.text.strip() == button_text:
                selected_service = service
                break

    if not selected_service:
        # عرض الخدمات مرة أخرى مع رسالة خطأ
        await message.answer(
            "⚠️ الخدمة المختارة غير موجودة. يرجى النقر مباشرة على زر الخدمة من القائمة.",
            reply_markup=reply.get_services_keyboard(services)
        )
        return

    # تخزين الخدمة المختارة
    await state.update_data(selected_service=selected_service)

    # عرض تفاصيل الخدمة
    from utils.common import format_service_info
    service_text = format_service_info(selected_service)

    # طلب إدخال الرابط
    await message.answer(
        f"{service_text}\n\n"
        f"🔗 يرجى إدخال الرابط الخاص بالطلب:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_cancel_keyboard()
    )

    # تعيين حالة إدخال الرابط
    await state.set_state(OrderState.entering_link)

@router.message(OrderState.entering_link)
async def process_link_input(message: Message, state: FSMContext):
    """معالج إدخال الرابط"""
    # إلغاء الطلب
    if message.text == "❌ إلغاء":
        await state.clear()
        await message.answer(
            "🔄 تم إلغاء الطلب والعودة إلى القائمة الرئيسية.",
            reply_markup=reply.get_main_keyboard()
        )
        return

    # التحقق من الرابط (يمكن إضافة تحققات إضافية)
    link = message.text.strip()

    if not link.startswith(("http://", "https://")):
        await message.answer(
            "⚠️ يرجى إدخال رابط صحيح يبدأ بـ http:// أو https://",
            reply_markup=reply.get_cancel_keyboard()
        )
        return

    # تخزين الرابط
    await state.update_data(link=link)

    # الحصول على البيانات المخزنة
    data = await state.get_data()
    selected_service = data.get("selected_service", {})

    # الحصول على الحد الأدنى والأقصى للطلب
    min_order = selected_service.get("min", MIN_ORDER)
    max_order = selected_service.get("max", 10000)

    # طلب إدخال الكمية
    await message.answer(
        f"🔢 يرجى إدخال الكمية المطلوبة:\n"
        f"🔹 الحد الأدنى: {min_order}\n"
        f"🔹 الحد الأقصى: {max_order}",
        reply_markup=reply.get_cancel_keyboard()
    )

    # تعيين حالة إدخال الكمية
    await state.set_state(OrderState.entering_quantity)

@router.message(OrderState.entering_quantity)
async def process_quantity_input(message: Message, state: FSMContext):
    """معالج إدخال الكمية"""
    # إلغاء الطلب
    if message.text == "❌ إلغاء":
        await state.clear()
        await message.answer(
            "🔄 تم إلغاء الطلب والعودة إلى القائمة الرئيسية.",
            reply_markup=reply.get_main_keyboard()
        )
        return

    # التحقق من صحة الإدخال
    try:
        quantity = int(message.text.strip())
    except ValueError:
        await message.answer(
            "⚠️ يرجى إدخال رقم صحيح للكمية.",
            reply_markup=reply.get_cancel_keyboard()
        )
        return

    # الحصول على البيانات المخزنة
    data = await state.get_data()
    selected_service = data.get("selected_service", {})

    # الحصول على الحد الأدنى والأقصى للطلب
    try:
        min_order = int(selected_service.get("min", MIN_ORDER))
    except (ValueError, TypeError):
        min_order = MIN_ORDER

    try:
        max_order = int(selected_service.get("max", 10000))
    except (ValueError, TypeError):
        max_order = 10000

    # التحقق من أن الكمية ضمن الحدود
    if quantity < min_order or quantity > max_order:
        await message.answer(
            f"⚠️ الكمية المدخلة خارج الحدود المسموحة.\n"
            f"🔹 الحد الأدنى: {min_order}\n"
            f"🔹 الحد الأقصى: {max_order}",
            reply_markup=reply.get_cancel_keyboard()
        )
        return

    # تخزين الكمية
    await state.update_data(quantity=quantity)

    # حساب السعر
    try:
        rate = float(selected_service.get("rate", 0))
    except (ValueError, TypeError):
        # في حالة كان السعر نصًا غير قابل للتحويل
        await message.answer(
            "⚠️ حدث خطأ في حساب سعر الخدمة. يرجى المحاولة مرة أخرى أو اختيار خدمة أخرى.",
            reply_markup=reply.get_cancel_keyboard()
        )
        return

    # حساب السعر بناءً على نوع الخدمة
    try:
        max_order_check = int(selected_service.get("max", 0)) if isinstance(selected_service.get("max"), str) else selected_service.get("max", 0)
        if max_order_check == 1:
            # إذا كان الحد الأقصى 1، فهذا يعني أن السعر للباقة
            price = rate * quantity
        else:
            # وإلا، فالسعر لكل 1000
            price = (rate / 1000) * quantity
    except (ValueError, TypeError) as e:
        # تسجيل الخطأ
        logger.error(f"خطأ في حساب السعر: {e}")
        # في حالة حدوث خطأ، نستخدم الحساب الافتراضي
        price = (rate / 1000) * quantity if rate > 0 else 0

    # تخزين السعر
    await state.update_data(price=price)

    # التأكد من وجود سجل للمستخدم إذا لم يكن موجودًا
    try:
        # الحصول على رصيد المستخدم
        user_data = await get_user(message.from_user.id)

        # إنشاء المستخدم إذا لم يكن موجودًا
        if not user_data:
            from database.core import create_user
            username = message.from_user.username or "غير محدد"
            full_name = message.from_user.full_name or "غير محدد"
            await create_user(message.from_user.id, username, full_name)
            # الحصول على بيانات المستخدم بعد الإنشاء
            user_data = await get_user(message.from_user.id)
            if not user_data:
                raise Exception("فشل إنشاء المستخدم في قاعدة البيانات")

        balance = user_data.get("balance", 0)
    except Exception as e:
        # تسجيل الخطأ
        logger.error(f"خطأ في الحصول على بيانات المستخدم: {e}")
        await message.answer(
            "⚠️ حدث خطأ في استرجاع بيانات حسابك. يرجى المحاولة مرة أخرى لاحقًا.",
            reply_markup=reply.get_main_keyboard()
        )
        await state.clear()
        return

    # التحقق من صحة قيمة الرصيد
    if not isinstance(balance, (int, float)):
        try:
            balance = float(balance)
        except (ValueError, TypeError):
            balance = 0

    # إنشاء رسالة التأكيد
    # الحصول على سعر الخدمة الأصلي للعرض
    service_rate = selected_service.get("rate", 0)
    try:
        service_rate = float(service_rate)
    except (ValueError, TypeError):
        service_rate = 0

    # تحديد نوع تنسيق السعر (للباقة أو لكل 1000)
    try:
        max_order_check = int(selected_service.get("max", 0)) if isinstance(selected_service.get("max"), str) else selected_service.get("max", 0)
        price_format = "للباقة" if max_order_check == 1 else "لكل 1000"
    except (ValueError, TypeError):
        price_format = "لكل 1000"

    confirmation_text = (
        f"📋 <b>تأكيد الطلب:</b>\n\n"
        f"🔹 <b>الخدمة:</b> {selected_service.get('name', 'غير محدد')}\n"
        f"🔗 <b>الرابط:</b> {data.get('link', 'غير محدد')}\n"
        f"🔢 <b>الكمية:</b> {quantity}\n"
        f"💸 <b>سعر الخدمة:</b> ${format_money(service_rate)} {price_format}\n"
        f"💰 <b>إجمالي السعر:</b> ${format_money(price)}\n\n"
    )

    # التحقق من كفاية الرصيد
    if balance < price:
        confirmation_text += (
            f"⚠️ <b>رصيدك الحالي:</b> ${format_money(balance)}\n"
            f"⚠️ <b>رصيدك غير كافٍ لإتمام الطلب.</b>\n"
            f"💸 يرجى شحن رصيدك أولاً."
        )

        await message.answer(
            confirmation_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply.get_main_keyboard()
        )

        # إنهاء العملية
        await state.clear()
        return

    # إذا كان الرصيد كافياً
    confirmation_text += (
        f"✅ <b>رصيدك الحالي:</b> ${format_money(balance)}\n"
        f"✅ <b>الرصيد المتبقي بعد الخصم:</b> ${format_money(balance - price)}\n\n"
        f"⬇️ هل تريد تأكيد الطلب؟"
    )

    # إرسال رسالة التأكيد مع أزرار نعم/لا
    await message.answer(
        confirmation_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_confirmation_keyboard()
    )

    # تعيين حالة تأكيد الطلب
    await state.set_state(OrderState.confirming_order)

@router.message(OrderState.confirming_order)
async def process_order_confirmation(message: Message, state: FSMContext):
    """معالج تأكيد الطلب"""
    # التحقق من الإجابة
    if message.text == "✅ نعم":
        try:
            # الحصول على البيانات المخزنة
            data = await state.get_data()
            selected_service = data.get("selected_service", {})
            link = data.get("link", "")
            quantity = data.get("quantity", 0)
            price = data.get("price", 0)

            # إرسال الطلب إلى API
            service_id = selected_service.get("service", 0)

            # إظهار رسالة الانتظار
            processing_message = await message.answer(
                "⏳ جاري معالجة طلبك... يرجى الانتظار."
            )

            # إرسال الطلب إلى API
            order_result = await add_order(service_id, link, quantity)

            if not order_result:
                await message.answer(
                    "❌ حدث خطأ أثناء الاتصال بنظام الطلبات. يرجى المحاولة مرة أخرى لاحقًا.",
                    reply_markup=reply.get_main_keyboard()
                )
                await state.clear()
                return

            if "error" in order_result:
                error_message = order_result.get("error", "خطأ غير معروف")
                await message.answer(
                    f"❌ حدث خطأ أثناء إرسال الطلب: {error_message}",
                    reply_markup=reply.get_main_keyboard()
                )
                await state.clear()
                return

            if "order" not in order_result:
                await message.answer(
                    "❌ حدث خطأ في إنشاء الطلب. يرجى التحقق من البيانات والمحاولة مرة أخرى.",
                    reply_markup=reply.get_main_keyboard()
                )
                await state.clear()
                return

            # استخراج معرف الطلب
            order_id = order_result.get("order", "غير محدد")

            # خصم المبلغ من رصيد المستخدم
            success = await update_user_balance(message.from_user.id, price, "subtract")

            if not success:
                # إذا فشلت عملية خصم الرصيد، نسجل ذلك ونخبر المستخدم
                logger.error(f"فشل في خصم الرصيد: المستخدم: {message.from_user.id}, المبلغ: {price}")
                await message.answer(
                    "❌ حدث خطأ أثناء خصم المبلغ من رصيدك. يرجى التواصل مع الإدارة.",
                    reply_markup=reply.get_main_keyboard()
                )
                await state.clear()
                return

            # إنشاء سجل للطلب في قاعدة البيانات (إذا كانت هناك وظيفة كهذه)
            try:
                from database.core import create_order
                await create_order(
                    message.from_user.id,
                    order_id,
                    service_id,
                    selected_service.get("name", "غير محدد"),
                    link,
                    quantity,
                    price
                )
            except Exception as e:
                # نسجل الخطأ دون إيقاف العملية
                logger.error(f"خطأ في تسجيل الطلب في قاعدة البيانات: {e}")

            # الحصول على سعر الخدمة الأصلي للعرض
            service_rate = selected_service.get("rate", 0)
            try:
                service_rate = float(service_rate)
            except (ValueError, TypeError):
                service_rate = 0

            # تحديد نوع تنسيق السعر (للباقة أو لكل 1000)
            try:
                max_order_check = int(selected_service.get("max", 0)) if isinstance(selected_service.get("max"), str) else selected_service.get("max", 0)
                price_format = "للباقة" if max_order_check == 1 else "لكل 1000"
            except (ValueError, TypeError):
                price_format = "لكل 1000"

            # إرسال رسالة نجاح الطلب
            await message.answer(
                f"✅ تم إرسال طلبك بنجاح!\n\n"
                f"🔹 <b>رقم الطلب:</b> {order_id}\n"
                f"🔹 <b>الخدمة:</b> {selected_service.get('name', 'غير محدد')}\n"
                f"🔗 <b>الرابط:</b> {link}\n"
                f"🔢 <b>الكمية:</b> {quantity}\n"
                f"💸 <b>سعر الخدمة:</b> ${format_money(service_rate)} {price_format}\n"
                f"💰 <b>إجمالي السعر:</b> ${format_money(price)}\n\n"
                f"⏱ جارٍ معالجة طلبك. يمكنك متابعة حالة الطلب من خلال 'طلباتي السابقة'.",
                parse_mode=ParseMode.HTML,
                reply_markup=reply.get_main_keyboard()
            )

            # تسجيل الطلب في السجل
            logger.info(f"تم إنشاء طلب جديد: المستخدم: {message.from_user.id}, رقم الطلب: {order_id}, الخدمة: {service_id}, المبلغ: {price}")

        except Exception as e:
            # تسجيل أي خطأ غير متوقع
            logger.error(f"خطأ غير متوقع أثناء معالجة الطلب: {e}")
            await message.answer(
                "❌ حدث خطأ غير متوقع أثناء معالجة الطلب. يرجى المحاولة مرة أخرى لاحقًا.",
                reply_markup=reply.get_main_keyboard()
            )

    elif message.text == "❌ لا":
        # إلغاء الطلب
        await message.answer(
            "🔄 تم إلغاء الطلب والعودة إلى القائمة الرئيسية.",
            reply_markup=reply.get_main_keyboard()
        )
    else:
        # إجابة غير صالحة
        await message.answer(
            "⚠️ يرجى الاختيار من الأزرار المتاحة.",
            reply_markup=reply.get_confirmation_keyboard()
        )
        return

    # إنهاء العملية
    await state.clear()

@router.message(F.text == "🔍 طلباتي السابقة")
async def show_my_orders(message: Message, state: FSMContext):
    """معالج عرض طلبات المستخدم السابقة"""
    user_id = message.from_user.id

    try:
        # الحصول على طلبات المستخدم من قاعدة البيانات المحلية
        from database.core import get_user_orders as get_local_orders
        orders, total = await get_local_orders(user_id)

        if not orders:
            await message.answer(
                "📭 لا توجد طلبات سابقة لديك حتى الآن.",
                reply_markup=reply.get_main_keyboard()
            )
            return

        # تخزين البيانات في الحالة
        await state.update_data(orders=orders, total=total, page=1)

        # عرض الصفحة الأولى
        await display_orders_page(message, state)

        # تعيين حالة عرض الطلبات
        await state.set_state(UserState.viewing_orders)
    except Exception as e:
        logger.error(f"خطأ في عرض طلبات المستخدم: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء استرجاع طلباتك السابقة. يرجى المحاولة مرة أخرى لاحقًا.",
            reply_markup=reply.get_main_keyboard()
        )

async def display_orders_page(message: Message, state: FSMContext):
    """عرض صفحة من الطلبات السابقة"""
    # الحصول على البيانات
    data = await state.get_data()
    orders = data.get("orders", [])
    total = data.get("total", 0)
    page = data.get("page", 1)
    per_page = 5  # عدد العناصر في الصفحة

    # حساب عدد الصفحات
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    # تأكد من أن الصفحة ضمن النطاق
    page = max(1, min(page, total_pages))

    # إنشاء رسالة بالطلبات
    orders_text = f"📋 <b>طلباتك السابقة ({total}):</b>\n"
    orders_text += f"📄 <b>الصفحة:</b> {page}/{total_pages}\n\n"

    # حساب النطاق للصفحة الحالية
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(orders))

    # تنسيق حالة الطلب
    status_map = {
        "pending": "⏳ قيد الانتظار",
        "in_progress": "🔄 قيد التنفيذ",
        "completed": "✅ مكتمل",
        "partial": "⚠️ جزئي",
        "canceled": "❌ ملغي",
        "processing": "⚙️ قيد المعالجة",
        "refunded": "💸 مسترجع",
        "failed": "❗ فشل"
    }

    # إضافة الطلبات
    for i in range(start_idx, end_idx):
        order = orders[i]
        # استخراج المعلومات بشكل صحيح مع التحقق من وجود القيم
        order_id = order.get("order_id", "غير محدد")
        service_id = order.get("service_id", "غير محدد")
        service_name = order.get("service_name", "غير محدد")
        link = order.get("link", "غير محدد")
        quantity = order.get("quantity", 0)
        price = order.get("amount", 0)
        created_at = order.get("created_at", "غير محدد")
        status = order.get("status", "pending")
        remains = order.get("remains", quantity)  # استخدام الكمية الأصلية كقيمة افتراضية

        # تنسيق الرابط (عرض جزء فقط منه لتجنب النصوص الطويلة)
        if len(link) > 40:
            displayed_link = link[:37] + "..."
        else:
            displayed_link = link

        # محاولة جلب حالة الطلب مباشرة من API المزود
        formatted_status = status.lower().replace("_", " ")
        status_text = status_map.get(formatted_status, "⏳ قيد الانتظار")
        
        # تجربة جلب الحالة من API فقط للطلبات ذات المعرف الرقمي
        if order_id.isdigit():
            try:
                from services.api import check_order_status
                # استدعاء واجهة API للتحقق من حالة الطلب
                api_status_result = await check_order_status(order_id)
                logger.debug(f"استجابة API لحالة الطلب #{order_id}: {api_status_result}")
                
                if "error" not in api_status_result:
                    # استخراج البيانات من الاستجابة
                    api_remains = api_status_result.get("remains", "0")
                    api_status_raw = api_status_result.get("status", "")
                    
                    # تحويل حالة API إلى تنسيق قاعدة البيانات المحلية
                    api_status = api_status_raw.lower().strip() if api_status_raw else ""
                    
                    # دالة لتحويل حالة API إلى تنسيق قاعدة البيانات
                    def convert_api_status(status_str):
                        """تحويل حالة API إلى تنسيق قاعدة البيانات المحلية"""
                        status_map = {
                            "pending": "pending",
                            "in progress": "processing",
                            "processing": "processing", 
                            "completed": "completed",
                            "partial": "partial",
                            "canceled": "canceled",
                            "refunded": "refunded",
                            "failed": "failed"
                        }
                        return status_map.get(status_str.lower(), "pending")
                    
                    # تحويل حالة API إلى تنسيق قاعدة البيانات
                    normalized_api_status = convert_api_status(api_status)
                    
                    try:
                        # تحويل قيمة remains إلى رقم صحيح
                        api_remains_int = int(float(api_remains))
                        
                        # تحديث قيمة remains في قاعدة البيانات
                        from database.core import update_order_remains_simple
                        await update_order_remains_simple(order_id, api_remains_int)
                        
                        # تحديث المتغير المحلي للاستخدام في عرض تفاصيل الطلب
                        remains = api_remains_int
                        
                        # تسجيل تغييرات حالة الطلب
                        if normalized_api_status != formatted_status:
                            logger.info(f"تحديث حالة الطلب #{order_id}: من API ({api_status_raw}) -> محولة ({normalized_api_status}) <- كانت ({formatted_status})")
                            
                            # تحديث الحالة في قاعدة البيانات
                            from database.core import update_order_status
                            await update_order_status(order_id, normalized_api_status)
                            
                            # تحديث المتغير المحلي لعرض الحالة في رسالة التفاصيل
                            formatted_api_status = normalized_api_status.replace("_", " ")
                            status_text = status_map.get(formatted_api_status, f"⏳ {normalized_api_status}")
                    
                    except (ValueError, TypeError) as e:
                        # تسجيل الخطأ ولكن الاستمرار في التنفيذ
                        logger.error(f"خطأ في معالجة بيانات الطلب #{order_id} من API: {e}")
                        logger.debug(f"بيانات API: remains={api_remains}, status={api_status_raw}")
            except Exception as e:
                # تسجيل الخطأ دون التأثير على سير العمل
                logger.error(f"خطأ في جلب حالة الطلب #{order_id} من API: {e}")

        # تنسيق التاريخ بشكل أفضل إذا كان ممكنًا
        try:
            if isinstance(created_at, str) and len(created_at) > 19:
                created_at = created_at[:19].replace("T", " ")
        except Exception:
            pass

        # إنشاء نص معلومات الطلب
        orders_text += (
            f"🔖 <b>رقم الطلب:</b> #{order_id}\n"
            f"🔹 <b>الخدمة:</b> {service_name} (#{service_id})\n"
            f"🔗 <b>الرابط:</b> {displayed_link}\n"
            f"🔢 <b>الكمية:</b> {quantity}\n"
            f"🔄 <b>المتبقي:</b> {remains}\n"
            f"💰 <b>السعر:</b> ${format_money(price)}\n"
            f"📊 <b>الحالة:</b> {status_text}\n"
            f"📅 <b>التاريخ:</b> {created_at}\n\n"
        )

    # إضافة زر التحقق من حالة الطلب مباشرة من API
    keyboard = reply.get_orders_detail_keyboard(page, total_pages)
    
    await message.answer(
        orders_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

@router.message(UserState.viewing_orders, F.text == "⬅️ السابق")
async def previous_orders_page(message: Message, state: FSMContext):
    """معالج الانتقال للصفحة السابقة من الطلبات"""
    data = await state.get_data()
    page = data.get("page", 1)
    
    # تحديث الصفحة
    if page > 1:
        await state.update_data(page=page-1)
    
    # عرض الصفحة
    await display_orders_page(message, state)

@router.message(UserState.viewing_orders, F.text == "➡️ التالي")
async def next_orders_page(message: Message, state: FSMContext):
    """معالج الانتقال للصفحة التالية من الطلبات"""
    data = await state.get_data()
    page = data.get("page", 1)
    total = data.get("total", 0)
    per_page = 5
    
    # حساب إجمالي الصفحات
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    # تحديث الصفحة
    if page < total_pages:
        await state.update_data(page=page+1)
    
    # عرض الصفحة
    await display_orders_page(message, state)

# تم حذف معالج زر التحقق من حالة الطلب وحالة إدخال رقم الطلب
# لأننا الآن نقوم بالتحقق من حالة الطلب تلقائيًا عند عرض تفاصيل الطلب

@router.message(UserState.viewing_orders, F.text == "🔙 العودة")
async def back_from_orders(message: Message, state: FSMContext):
    """معالج العودة من عرض الطلبات"""
    await state.clear()
    await message.answer(
        "🔄 تم العودة إلى القائمة الرئيسية.",
        reply_markup=reply.get_main_keyboard()
    )

@router.message(F.text == "💰 رصيدي")
async def show_my_balance(message: Message):
    """معالج عرض رصيد المستخدم"""
    user_id = message.from_user.id

    try:
        # الحصول على بيانات المستخدم
        user_data = await get_user(user_id)

        # إنشاء المستخدم إذا لم يكن موجودًا
        if not user_data:
            from database.core import create_user
            username = message.from_user.username or "غير محدد"
            full_name = message.from_user.full_name or "غير محدد"
            await create_user(user_id, username, full_name)
            # الحصول على بيانات المستخدم بعد الإنشاء
            user_data = await get_user(user_id)
            if not user_data:
                raise Exception("فشل إنشاء المستخدم في قاعدة البيانات")

        # استخراج البيانات
        balance = user_data.get("balance", 0)
        username = user_data.get("username", "غير محدد")
        full_name = user_data.get("full_name", "غير محدد")
        created_at = user_data.get("created_at", "غير محدد")
    except Exception as e:
        # تسجيل الخطأ
        logger.error(f"خطأ في الحصول على بيانات المستخدم: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء استرجاع بيانات حسابك. يرجى المحاولة مرة أخرى لاحقًا.",
            reply_markup=reply.get_main_keyboard()
        )
        return

    # إنشاء رسالة الرصيد
    balance_text = (
        f"💰 <b>معلومات حسابك:</b>\n\n"
        f"👤 <b>المستخدم:</b> {full_name}\n"
        f"🔹 <b>اسم المستخدم:</b> @{username}\n"
        f"💵 <b>الرصيد الحالي:</b> ${format_money(balance)}\n"
        f"📅 <b>تاريخ إنشاء الحساب:</b> {created_at}\n\n"
        f"💡 لشحن رصيدك، اضغط على زر 'إيداع رصيد'."
    )

    # إرسال الرسالة
    await message.answer(
        balance_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_main_keyboard()
    )

@router.message(F.text == "💸 إيداع رصيد")
async def deposit_balance(message: Message, state: FSMContext):
    """معالج بدء عملية إيداع الرصيد"""
    try:
        # التأكد من وجود المستخدم في قاعدة البيانات
        user_data = await get_user(message.from_user.id)
        if not user_data:
            # إنشاء المستخدم إذا لم يكن موجوداً
            from database.core import create_user
            username = message.from_user.username or "غير محدد"
            full_name = message.from_user.full_name or "غير محدد"
            await create_user(message.from_user.id, username, full_name)

        # عرض طرق الدفع
        payment_methods_text = (
            f"💳 <b>طرق الدفع المتاحة:</b>\n\n"
            f"يرجى اختيار طريقة الدفع المناسبة لك:"
        )

        # إرسال الرسالة مع أزرار طرق الدفع
        await message.answer(
            payment_methods_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply.get_payment_methods_keyboard()
        )

        # تعيين حالة اختيار طريقة الدفع
        await state.set_state(DepositState.selecting_payment_method)
    except Exception as e:
        logger.error(f"خطأ في بدء عملية الإيداع: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء بدء عملية الإيداع. يرجى المحاولة مرة أخرى لاحقًا.",
            reply_markup=reply.get_main_keyboard()
        )

@router.message(DepositState.selecting_payment_method)
async def process_payment_method_selection(message: Message, state: FSMContext):
    """معالج اختيار طريقة الدفع"""
    try:
        # التحقق من صحة الاختيار
        if message.text == "🔙 العودة":
            # العودة للقائمة الرئيسية
            await state.clear()
            await message.answer(
                "🔄 تم العودة إلى القائمة الرئيسية.",
                reply_markup=reply.get_main_keyboard()
            )
            return

        payment_method = None
        payment_info = None

        # التحقق من طريقة الدفع المختارة
        for method_key, method_data in config.PAYMENT_METHODS.items():
            if message.text == method_data["name"]:
                payment_method = method_key
                payment_info = method_data
                break

        if not payment_method:
            await message.answer(
                "⚠️ يرجى اختيار طريقة دفع صحيحة من القائمة.",
                reply_markup=reply.get_payment_methods_keyboard()
            )
            return

        # تخزين طريقة الدفع
        await state.update_data(payment_method=payment_method, payment_info=payment_info)

        # طلب إدخال المبلغ
        min_deposit = payment_info.get("min_deposit", 0)

        await message.answer(
            f"💰 يرجى إدخال المبلغ الذي ترغب في إيداعه:\n"
            f"🔹 الحد الأدنى للإيداع: {min_deposit}",
            reply_markup=reply.get_cancel_keyboard()
        )

        # تعيين حالة إدخال المبلغ
        await state.set_state(DepositState.entering_amount)
    except Exception as e:
        logger.error(f"خطأ في اختيار طريقة الدفع: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء اختيار طريقة الدفع. يرجى المحاولة مرة أخرى لاحقًا.",
            reply_markup=reply.get_main_keyboard()
        )
        await state.clear()

@router.message(DepositState.entering_amount)
async def process_amount_input(message: Message, state: FSMContext):
    """معالج إدخال مبلغ الإيداع"""
    try:
        # إلغاء العملية
        if message.text == "❌ إلغاء":
            await state.clear()
            await message.answer(
                "🔄 تم إلغاء عملية الإيداع والعودة إلى القائمة الرئيسية.",
                reply_markup=reply.get_main_keyboard()
            )
            return

        # التحقق من صحة المبلغ
        is_valid, amount, error_msg = validate_number(message.text)

        if not is_valid:
            await message.answer(
                f"⚠️ {error_msg}",
                reply_markup=reply.get_cancel_keyboard()
            )
            return

        # الحصول على البيانات المخزنة
        data = await state.get_data()
        payment_info = data.get("payment_info", {})

        # التحقق من الحد الأدنى
        min_deposit = payment_info.get("min_deposit", 0)

        if amount < min_deposit:
            await message.answer(
                f"⚠️ المبلغ المدخل أقل من الحد الأدنى ({min_deposit}).",
                reply_markup=reply.get_cancel_keyboard()
            )
            return

        # تخزين المبلغ
        await state.update_data(amount=amount)

        # عرض معلومات الدفع
        payment_method = data.get("payment_method", "")

        # رسالة الانتظار
        wait_message = await message.answer("⏳ جارٍ إعداد معلومات الدفع...")

        # إنشاء معلومات الدفع حسب الطريقة
        payment_details = ""
        qr_code = None

        if payment_method == "USDT":
            # استخراج عنوان المحفظة من البيئة
            wallet = payment_info.get("wallet", "")
            network = payment_info.get("network", "TRC-20")
            payment_details = (
                f"🔹 <b>العنوان:</b> <code>{wallet}</code>\n"
                f"🔹 <b>الشبكة:</b> {network}\n"
                f"💡 يرجى نسخ العنوان واستخدامه للتحويل."
            )
        elif payment_method == "BARIDIMOB":
            # استخراج رقم الحساب من البيئة
            account = payment_info.get("account", "")
            holder_name = payment_info.get("holder_name", "")
            payment_details = (
                f"🔹 <b>رقم الحساب:</b> <code>{account}</code>\n"
                f"🔹 <b>اسم صاحب الحساب:</b> {holder_name}\n"
                f"💡 يرجى استخدام تطبيق بريدي موب للتحويل."
            )

        # إنشاء طلب إيداع في قاعدة البيانات
        deposit_id = await create_deposit_request(
            message.from_user.id,
            amount,
            payment_method
        )

        if not deposit_id:
            await message.answer(
                "⚠️ حدث خطأ أثناء إنشاء طلب الإيداع. يرجى المحاولة مرة أخرى لاحقًا.",
                reply_markup=reply.get_main_keyboard()
            )
            await state.clear()
            return

        # تخزين معرف طلب الإيداع
        await state.update_data(deposit_id=deposit_id)

        # حذف رسالة الانتظار
        await wait_message.delete()

        # إنشاء رسالة معلومات الدفع مع نص تحذيري
        payment_text = (
            f"💳 <b>معلومات الدفع:</b>\n\n"
            f"🔹 <b>طريقة الدفع:</b> {payment_info.get('name', '')}\n"
            f"🔹 <b>المبلغ:</b> {format_money(amount)}\n\n"
            f"{payment_details}\n\n"
            f"⚠️ <b>تنبيه هام:</b>\n"
            f"✅ لحماية أموالك ومصداقية تعاملنا، <b>إرسال الإيصال إجباري</b> بعد إتمام عملية الدفع. إذا لم تقم بالإيداع بعد، يمكنك الضغط على زر \"لم أقم بالإيداع بعد\" للعودة.\n\n"
            f"⬇️ <b>بعد إكمال عملية الدفع</b>، يرجى إرسال صورة لإيصال الدفع أو رقم العملية هنا.\n\n"
            f"🔴 <b>ملاحظة:</b> إذا قمت بالإيداع عن طريق الخطأ ولم ترسل الإيصال، يجب التواصل مع المدير مباشرة."
        )

        # إرسال الرسالة مع لوحة مفاتيح خاصة (زر "لم أقم بالإيداع بعد")
        await message.answer(
            payment_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply.get_deposit_cancel_keyboard()
        )

        # تعيين حالة إرسال الإيصال
        await state.set_state(DepositState.sending_receipt)
    except Exception as e:
        logger.error(f"خطأ في معالجة مبلغ الإيداع: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء معالجة مبلغ الإيداع. يرجى المحاولة مرة أخرى لاحقًا.",
            reply_markup=reply.get_main_keyboard()
        )
        await state.clear()

@router.message(DepositState.sending_receipt)
async def process_receipt(message: Message, state: FSMContext):
    """معالج إرسال إيصال الدفع"""
    try:
        # التعامل مع أزرار إلغاء العملية أو العودة
        if message.text == "❌ إلغاء عملية الإيداع":
            # إلغاء عملية الإيداع
            data = await state.get_data()
            deposit_id = data.get("deposit_id", 0)

            # تحديث حالة طلب الإيداع (إلغاء)
            from database.deposit import reject_deposit
            await reject_deposit(deposit_id, admin_note="تم الإلغاء بواسطة المستخدم")

            await state.clear()
            await message.answer(
                "🔄 تم إلغاء عملية الإيداع والعودة إلى القائمة الرئيسية.",
                reply_markup=reply.get_main_keyboard()
            )
            return

        if message.text == "⚠️ لم أقم بالإيداع بعد":
            # المستخدم لم يقم بالإيداع بعد
            data = await state.get_data()
            deposit_id = data.get("deposit_id", 0)

            # تحديث حالة طلب الإيداع (إلغاء - لم يتم الإيداع)
            from database.deposit import reject_deposit
            await reject_deposit(deposit_id, admin_note="لم يتم الإيداع (تم التأكيد من قبل المستخدم)")

            await state.clear()
            await message.answer(
                "✅ شكراً على توضيح أنك لم تقم بالإيداع بعد. لقد تم إلغاء طلب الإيداع الحالي.\n\n"
                "يمكنك بدء عملية إيداع جديدة عندما تكون مستعداً.",
                reply_markup=reply.get_main_keyboard()
            )
            return

        # الحصول على البيانات المخزنة
        data = await state.get_data()
        deposit_id = data.get("deposit_id", 0)
        amount = data.get("amount", 0)
        payment_method = data.get("payment_method", "")
        payment_info = data.get("payment_info", {})

        # تخزين معلومات الإيصال
        receipt_info = ""
        transaction_id = None
        file_id = None

        # التحقق من نوع الرسالة
        if message.photo:
            # إذا كانت الرسالة تحتوي على صورة
            file_id = message.photo[-1].file_id
            receipt_info = f"صورة إيصال (ID: {file_id})"
            # إذا كان هناك نص مع الصورة، قد يكون رقم العملية
            if message.caption:
                transaction_id = message.caption.strip()
                receipt_info += f" مع رقم عملية: {transaction_id}"
        elif message.document:
            # إذا كانت الرسالة تحتوي على ملف
            file_id = message.document.file_id
            receipt_info = f"ملف إيصال: {message.document.file_name} (ID: {file_id})"
            # إذا كان هناك نص مع الملف، قد يكون رقم العملية
            if message.caption:
                transaction_id = message.caption.strip()
                receipt_info += f" مع رقم عملية: {transaction_id}"
        elif message.text:
            # إذا كانت الرسالة نصية (قد تكون رقم عملية)
            receipt_info = f"معلومات إيصال: {message.text}"
            transaction_id = message.text.strip()
        else:
            # نوع غير مدعوم
            await message.answer(
                "⚠️ يرجى إرسال صورة أو نص أو ملف كإيصال للدفع.\n\n"
                "⚠️ <b>تنبيه هام:</b> تأكد من أنك قمت بالإيداع فعلياً قبل إرسال الإيصال. إرسال إيصالات وهمية أو غير صحيحة يؤدي إلى حظر حسابك.\n\n"
                "👆 إذا لم تقم بالإيداع بعد، يرجى الضغط على زر \"لم أقم بالإيداع بعد\".",
                parse_mode=ParseMode.HTML,
                reply_markup=reply.get_deposit_cancel_keyboard()
            )
            return

        # تأكيد إضافي للمستخدم قبل إرسال الإيصال
        await state.update_data(
            receipt_info=receipt_info,
            transaction_id=transaction_id,
            file_id=file_id
        )
        
        # رسالة تأكيد مسؤولية المستخدم
        confirmation_message = (
            f"⚠️ <b>تأكيد المعلومات:</b>\n\n"
            f"🔹 <b>طريقة الدفع:</b> {payment_info.get('name', '')}\n"
            f"🔹 <b>المبلغ:</b> {format_money(amount)}\n\n"
            f"📝 <b>إقرار مسؤولية:</b>\n"
            f"أقر أنني قمت بعملية الإيداع بالفعل وأن المعلومات المُقدمة صحيحة. وأتحمل مسؤولية أي تلاعب أو معلومات خاطئة.\n\n"
            f"‼️ <b>ملاحظة هامة:</b> إذا قمت بإرسال إيصال وهمي أو غير صحيح، سيتم حظر حسابك.\n\n"
            f"👆 يرجى التأكيد على إرسال الإيصال أو التراجع."
        )
        
        # تغيير الحالة إلى تأكيد الإيصال
        await state.set_state(DepositState.confirming_receipt)
        
        # إرسال رسالة التأكيد مع أزرار التأكيد أو إلغاء
        await message.answer(
            confirmation_message,
            parse_mode=ParseMode.HTML,
            reply_markup=reply.get_confirmation_keyboard()
        )
        
    except Exception as e:
        logger.error(f"خطأ في معالجة إيصال الإيداع: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء معالجة إيصال الإيداع. يرجى المحاولة مرة أخرى لاحقًا.",
            reply_markup=reply.get_main_keyboard()
        )
        await state.clear()

@router.message(DepositState.confirming_receipt)
async def confirm_receipt_submission(message: Message, state: FSMContext):
    """تأكيد إرسال إيصال الإيداع"""
    try:
        if message.text == "✅ نعم":
            # الحصول على البيانات المخزنة
            data = await state.get_data()
            deposit_id = data.get("deposit_id", 0)
            amount = data.get("amount", 0)
            payment_info = data.get("payment_info", {})
            receipt_info = data.get("receipt_info", "")
            transaction_id = data.get("transaction_id")
            
            # تحديث معلومات الإيصال في قاعدة البيانات
            receipt_updated = await update_deposit_receipt(deposit_id, receipt_info)

            # تحديث رقم العملية إذا كان موجودًا
            if transaction_id and len(transaction_id) > 0:
                from database.deposit import update_deposit_transaction_id
                await update_deposit_transaction_id(deposit_id, transaction_id)

            if not receipt_updated:
                await message.answer(
                    "⚠️ حدث خطأ أثناء تحديث معلومات الإيصال. يرجى المحاولة مرة أخرى أو التواصل مع الإدارة.",
                    reply_markup=reply.get_deposit_cancel_keyboard()
                )
                return

            # إنشاء رسالة تأكيد الإيداع
            confirmation_text = (
                f"📝 <b>ملخص طلب الإيداع:</b>\n\n"
                f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
                f"🔹 <b>طريقة الدفع:</b> {payment_info.get('name', '')}\n"
                f"🔹 <b>المبلغ:</b> {format_money(amount)}\n"
                f"🔹 <b>الإيصال:</b> ✅ تم استلامه\n"
            )

            if transaction_id and len(transaction_id) > 0:
                confirmation_text += f"🔹 <b>رقم العملية:</b> {transaction_id}\n"

            confirmation_text += (
                f"\n⏱ <b>تم استلام طلبك وسيتم مراجعته من قبل الإدارة.</b>\n"
                f"سيتم إشعارك عند الموافقة على الطلب وإضافة المبلغ إلى رصيدك.\n\n"
                f"🔹 <b>وقت التقديم:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"💡 <b>يمكنك متابعة حالة طلبك من قسم \"تاريخ الإيداعات\".</b>"
            )

            # إرسال رسالة التأكيد
            await message.answer(
                confirmation_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply.get_main_keyboard()
            )

            # إرسال إشعار للمشرفين
            admin_notification = (
                f"💸 <b>طلب إيداع جديد:</b>\n\n"
                f"👤 <b>المستخدم:</b> {message.from_user.id} (@{message.from_user.username or 'بدون معرف'})\n"
                f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
                f"🔹 <b>طريقة الدفع:</b> {payment_info.get('name', '')}\n"
                f"🔹 <b>المبلغ:</b> {format_money(amount)}\n"
            )

            if transaction_id and len(transaction_id) > 0:
                admin_notification += f"🔹 <b>رقم العملية:</b> {transaction_id}\n"

            admin_notification += (
                f"🔹 <b>الإيصال:</b> {receipt_info}\n\n"
                f"⚡️ <b>للموافقة السريعة:</b> استخدم أمر 'قبول {deposit_id}' في قسم المشرف.\n"
                f"🔄 <b>للاسترداد:</b> استخدم أمر 'استرداد {deposit_id}' في حالة الإيداع الخاطئ."
            )
            
            # مسح الحالة بعد الانتهاء
            await state.clear()
            
        elif message.text == "❌ لا":
            # المستخدم تراجع عن إرسال الإيصال
            data = await state.get_data()
            deposit_id = data.get("deposit_id", 0)
            
            # تحديث حالة طلب الإيداع (إلغاء - المستخدم تراجع)
            from database.deposit import reject_deposit
            await reject_deposit(deposit_id, admin_note="تم إلغاء العملية من قبل المستخدم (تراجع عن إرسال الإيصال)")
            
            await message.answer(
                "🔄 تم إلغاء عملية الإيداع والعودة إلى القائمة الرئيسية.\n\n"
                "يمكنك بدء عملية إيداع جديدة عندما تكون مستعداً.",
                reply_markup=reply.get_main_keyboard()
            )
            
            # مسح الحالة بعد الانتهاء
            await state.clear()
            
        else:
            # رسالة غير صالحة
            await message.answer(
                "⚠️ يرجى اختيار أحد الخيارات المتاحة: نعم أو لا.",
                reply_markup=reply.get_confirmation_keyboard()
            )
            
    except Exception as e:
        logger.error(f"خطأ في تأكيد إيصال الإيداع: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء تأكيد إيصال الإيداع. يرجى المحاولة مرة أخرى لاحقًا.",
            reply_markup=reply.get_main_keyboard()
        )
        await state.clear()

        # محاولة الحصول على معلومات الإيداع من حالة المستخدم
        try:
            data = await state.get_data()
            deposit_id = data.get("deposit_id", 0)
            amount = data.get("amount", 0)
            payment_info = data.get("payment_info", {})
            payment_method = payment_info.get("name", "غير معروف")
            
            # إنشاء إشعار للمشرفين عن الخطأ
            error_notification = (
                f"⚠️ <b>حدث خطأ أثناء إكمال طلب إيداع:</b>\n\n"
                f"👤 <b>المستخدم:</b> {message.from_user.id} (@{message.from_user.username or 'بدون معرف'})\n"
                f"🔹 <b>رقم الطلب:</b> {deposit_id}\n"
                f"🔹 <b>المبلغ:</b> ${format_money(amount)}\n"
                f"🔹 <b>الخطأ:</b> {e}\n\n"
                f"يرجى التحقق من طلب الإيداع يدويًا."
            )
            
            # إرسال الإشعار لكافة المشرفين
            for admin_id in config.ADMIN_IDS:
                try:
                    bot = message.bot
                    # إرسال الإشعار للمشرف
                    await bot.send_message(
                        admin_id,
                        error_notification,
                        parse_mode=ParseMode.HTML
                    )

                    # إذا كانت هناك صورة أو مستند في الرسالة الحالية
                    if message.photo:
                        file_id = message.photo[-1].file_id
                        await bot.send_photo(
                            admin_id,
                            file_id,
                            caption=f"صورة إيصال لطلب الإيداع رقم {deposit_id} - ${format_money(amount)}"
                        )
                    elif message.document:
                        file_id = message.document.file_id
                        await bot.send_document(
                            admin_id,
                            file_id,
                            caption=f"ملف إيصال لطلب الإيداع رقم {deposit_id} - ${format_money(amount)}"
                        )
                except Exception as inner_e:
                    logger.error(f"خطأ في إرسال إشعار للمشرف {admin_id}: {inner_e}")

            # تسجيل الطلب في السجل
            logger.info(f"خطأ في طلب إيداع: {deposit_id}, المستخدم: {message.from_user.id}, المبلغ: {amount}, طريقة الدفع: {payment_method}")
        except Exception as data_e:
            logger.error(f"خطأ إضافي عند محاولة إرسال بيانات الخطأ: {data_e}")

        # إنهاء العملية
        await state.clear()
    except Exception as e:
        logger.error(f"خطأ في معالجة إيصال الدفع: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء معالجة إيصال الدفع. يرجى المحاولة مرة أخرى لاحقًا.",
            reply_markup=reply.get_main_keyboard()
        )
        await state.clear()

# إضافة معالج لعرض تاريخ الإيداعات للمستخدم
@router.message(F.text == "📜 تاريخ الإيداعات")
async def show_deposit_history(message: Message, state: FSMContext):
    """معالج عرض تاريخ الإيداعات للمستخدم"""
    try:
        user_id = message.from_user.id

        # الحصول على طلبات إيداع المستخدم
        from database.deposit import get_user_deposits
        deposits, total = await get_user_deposits(user_id)

        if not deposits:
            await message.answer(
                "📭 لا توجد طلبات إيداع سابقة لديك حتى الآن.",
                reply_markup=reply.get_main_keyboard()
            )
            return

        # تخزين البيانات في الحالة
        await state.update_data(deposits=deposits, total=total, page=1)

        # عرض الصفحة الأولى
        await display_deposits_page(message, state)

        # تعيين حالة عرض الإيداعات
        from states.order import UserState
        await state.set_state(UserState.viewing_deposits)
    except Exception as e:
        logger.error(f"خطأ في عرض تاريخ الإيداعات: {e}")
        await message.answer(
            "⚠️ حدث خطأ أثناء استرجاع تاريخ الإيداعات. يرجى المحاولة مرة أخرى لاحقًا.",
            reply_markup=reply.get_main_keyboard()
        )

async def display_deposits_page(message: Message, state: FSMContext):
    """عرض صفحة من تاريخ الإيداعات"""
    # الحصول على البيانات
    data = await state.get_data()
    deposits = data.get("deposits", [])
    total = data.get("total", 0)
    page = data.get("page", 1)
    per_page = 5  # عدد العناصر في الصفحة

    # حساب عدد الصفحات
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    # تأكد من أن الصفحة ضمن النطاق
    page = max(1, min(page, total_pages))

    # إنشاء رسالة بطلبات الإيداع
    deposits_text = f"📋 <b>تاريخ الإيداعات ({total}):</b>\n"
    deposits_text += f"📄 <b>الصفحة:</b> {page}/{total_pages}\n\n"

    # حساب النطاق للصفحة الحالية
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, len(deposits))

    # إضافة الإيداعات
    for i in range(start_idx, end_idx):
        deposit = deposits[i]
        status_map = {
            "pending": "🕒 قيد الانتظار",
            "approved": "✅ تمت الموافقة",
            "rejected": "❌ مرفوض"
        }
        status = status_map.get(deposit.get("status", "pending"), "🕒 قيد الانتظار")

        # تنسيق التاريخ بشكل أفضل إذا كان ممكنًا
        created_at = deposit.get("created_at", "غير محدد")
        try:
            if isinstance(created_at, str) and len(created_at) > 19:
                created_at = created_at[:19].replace("T", " ")
        except Exception:
            pass

        deposits_text += (
            f"🔹 <b>رقم الطلب:</b> {deposit.get('id', 'غير محدد')}\n"
            f"🔹 <b>المبلغ:</b> ${format_money(deposit.get('amount', 0))}\n"
            f"🔹 <b>طريقة الدفع:</b> {deposit.get('payment_method', 'غير محدد')}\n"
            f"🔹 <b>الحالة:</b> {status}\n"
            f"🔹 <b>التاريخ:</b> {created_at}\n\n"
        )

    # إرسال الرسالة مع أزرار التنقل
    pagination_keyboard = reply.get_pagination_keyboard(page, total_pages)
    
    await message.answer(
        deposits_text,
        parse_mode=ParseMode.HTML,
        reply_markup=pagination_keyboard
    )

@router.message(UserState.viewing_deposits, F.text == "⬅️ السابق")
async def previous_deposits_page(message: Message, state: FSMContext):
    """معالج الانتقال للصفحة السابقة من الإيداعات"""
    data = await state.get_data()
    page = data.get("page", 1)
    
    # تحديث الصفحة
    if page > 1:
        await state.update_data(page=page-1)
    
    # عرض الصفحة
    await display_deposits_page(message, state)

@router.message(UserState.viewing_deposits, F.text == "➡️ التالي")
async def next_deposits_page(message: Message, state: FSMContext):
    """معالج الانتقال للصفحة التالية من الإيداعات"""
    data = await state.get_data()
    page = data.get("page", 1)
    total = data.get("total", 0)
    per_page = 5
    
    # حساب إجمالي الصفحات
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    # تحديث الصفحة
    if page < total_pages:
        await state.update_data(page=page+1)
    
    # عرض الصفحة
    await display_deposits_page(message, state)

@router.message(UserState.viewing_deposits, F.text == "🔙 العودة")
async def back_from_deposits(message: Message, state: FSMContext):
    """معالج العودة من عرض الإيداعات"""
    await state.clear()
    await message.answer(
        "🔄 تم العودة إلى القائمة الرئيسية.",
        reply_markup=reply.get_main_keyboard()
    )

@router.message(F.text == "📞 اتصل بنا")
async def contact_us(message: Message):
    """معالج الاتصال بالإدارة"""
    # إنشاء نص الاتصال
    contact_text = f"""
📞 <b>اتصل بنا:</b>

إذا كان لديك أي استفسار أو مشكلة، يمكنك التواصل معنا عبر:

🔹 <b>البريد الإلكتروني:</b> {config.CONTACT_INFO["email"]}
🔹 <b>تيليجرام:</b> {config.ADMIN_USERNAME}
🔹 <b>الموقع:</b> {config.CONTACT_INFO["website"]}

نحن نعمل على مدار الساعة للرد على استفساراتك في أسرع وقت ممكن.
"""

    # إرسال الرسالة
    await message.answer(
        contact_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply.get_main_keyboard()
    )

@router.message(F.text == "🔄 تحديث")
async def refresh(message: Message):
    """معالج تحديث البوت"""
    await message.answer(
        "✅ تم تحديث البوت بنجاح!",
        reply_markup=reply.get_main_keyboard()
    )

# استيراد لوحات المفاتيح (يتم وضعه في نهاية الملف لتجنب الاستيراد الدائري)
from keyboards import reply

from datetime import datetime