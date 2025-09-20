"""
مدير لوحات المفاتيح للبوت
"""

import logging
from typing import Dict, Any, List, Optional, Union
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

class KeyboardManager:
    """مدير لوحات المفاتيح للبوت"""

    @staticmethod
    def create_list_keyboard(items: List[Dict[str, Any]], page: int, total_pages: int, 
                            key_field: str, value_field: str, callback_prefix: str) -> InlineKeyboardMarkup:
        """
        إنشاء لوحة مفاتيح قائمة مع التنقل بين الصفحات

        Args:
            items: قائمة العناصر
            page: رقم الصفحة الحالية
            total_pages: إجمالي عدد الصفحات
            key_field: اسم الحقل المستخدم كمفتاح
            value_field: اسم الحقل المستخدم كقيمة عرض
            callback_prefix: البادئة المستخدمة في بيانات الاستدعاء

        Returns:
            لوحة مفاتيح إنلاين
        """
        builder = InlineKeyboardBuilder()

        # إضافة أزرار العناصر
        for item in items:
            key = item.get(key_field, "")
            value = item.get(value_field, "")
            builder.button(
                text=value, 
                callback_data=f"{callback_prefix}_{key}"
            )

        # إضافة أزرار التنقل
        navigation = []

        if page > 1:
            navigation.append(InlineKeyboardButton(
                text="◀️ السابق",
                callback_data=f"{callback_prefix}_page_{page-1}"
            ))

        navigation.append(InlineKeyboardButton(
            text=f"📄 {page}/{total_pages}",
            callback_data=f"{callback_prefix}_page_info"
        ))

        if page < total_pages:
            navigation.append(InlineKeyboardButton(
                text="التالي ▶️",
                callback_data=f"{callback_prefix}_page_{page+1}"
            ))

        # إضافة أزرار التنقل
        if navigation:
            builder.row(*navigation)

        # زر العودة
        builder.row(InlineKeyboardButton(
            text="🔙 العودة",
            callback_data=f"{callback_prefix}_back"
        ))

        # تنظيم الأزرار (عنصرين في كل صف)
        keyboard = builder.as_markup()
        return keyboard

    @staticmethod
    def create_service_keyboard(services: List[Dict[str, Any]], page: int, 
                              items_per_page: int = 5) -> InlineKeyboardMarkup:
        """
        إنشاء لوحة مفاتيح للخدمات

        Args:
            services: قائمة الخدمات
            page: رقم الصفحة الحالية
            items_per_page: عدد العناصر في الصفحة الواحدة

        Returns:
            لوحة مفاتيح إنلاين
        """
        # حساب إجمالي عدد الصفحات
        total_pages = (len(services) + items_per_page - 1) // items_per_page

        # التأكد من أن رقم الصفحة ضمن النطاق الصحيح
        page = max(1, min(page, total_pages))

        # حساب نطاق العناصر للصفحة الحالية
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(services))

        # الحصول على الخدمات للصفحة الحالية
        page_services = services[start_idx:end_idx]

        # إنشاء لوحة المفاتيح
        builder = InlineKeyboardBuilder()

        # إضافة أزرار الخدمات
        for service in page_services:
            service_id = service.get("service")
            service_name = service.get("name")
            builder.button(
                text=service_name, 
                callback_data=f"service_{service_id}"
            )

        # تنظيم أزرار الخدمات (زر واحد في كل صف)
        builder.adjust(1)

        # إضافة أزرار التنقل
        navigation = []

        if page > 1:
            navigation.append(InlineKeyboardButton(
                text="◀️ السابق",
                callback_data=f"service_page_{page-1}"
            ))

        navigation.append(InlineKeyboardButton(
            text=f"📄 {page}/{total_pages}",
            callback_data="service_page_info"
        ))

        if page < total_pages:
            navigation.append(InlineKeyboardButton(
                text="التالي ▶️",
                callback_data=f"service_page_{page+1}"
            ))

        # إضافة أزرار التنقل
        if navigation:
            builder.row(*navigation)

        # زر العودة
        builder.row(InlineKeyboardButton(
            text="🔙 العودة",
            callback_data="back_to_main"
        ))

        return builder.as_markup()

    @staticmethod
    def create_confirmation_keyboard(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
        """
        إنشاء لوحة مفاتيح للتأكيد

        Args:
            confirm_data: بيانات الاستدعاء للتأكيد
            cancel_data: بيانات الاستدعاء للإلغاء

        Returns:
            لوحة مفاتيح إنلاين
        """
        builder = InlineKeyboardBuilder()

        builder.button(
            text="✅ نعم",
            callback_data=confirm_data
        )

        builder.button(
            text="❌ لا",
            callback_data=cancel_data
        )

        builder.adjust(2)  # وضع الزرين في صف واحد

        return builder.as_markup()

    @staticmethod
    def create_reply_keyboard(buttons: List[List[str]], resize_keyboard: bool = True, one_time_keyboard: bool = False) -> ReplyKeyboardMarkup:
        """
        إنشاء لوحة مفاتيح رد

        Args:
            buttons: مصفوفة تحتوي على أزرار اللوحة
            resize_keyboard: تغيير حجم اللوحة
            one_time_keyboard: لوحة مفاتيح لمرة واحدة

        Returns:
            ReplyKeyboardMarkup: لوحة المفاتيح
        """
        keyboard = []
        for row in buttons:
            keyboard_row = []
            for button_text in row:
                keyboard_row.append(KeyboardButton(text=button_text))
            keyboard.append(keyboard_row)

        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=resize_keyboard,
            one_time_keyboard=one_time_keyboard
        )

    @staticmethod
    def create_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> InlineKeyboardMarkup:
        """
        إنشاء لوحة مفاتيح إنلاين

        Args:
            buttons: مصفوفة تحتوي على أزرار اللوحة (text و callback_data و url)

        Returns:
            InlineKeyboardMarkup: لوحة المفاتيح
        """
        keyboard = []
        for row in buttons:
            keyboard_row = []
            for button_data in row:
                text = button_data.get("text", "")
                callback_data = button_data.get("callback_data")
                url = button_data.get("url")

                if url:
                    keyboard_row.append(InlineKeyboardButton(text=text, url=url))
                else:
                    keyboard_row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
            
            keyboard.append(keyboard_row)

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    #Removed redundant functions below as they are replaced by new functions above.