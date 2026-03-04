from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_payment_admin_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить оплату",
                    callback_data=f"admin_pay_ok:{payment_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить оплату",
                    callback_data=f"admin_pay_fail:{payment_id}",
                ),
            ]
        ]
    )


def build_manager_handled_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Обработано", callback_data="manager_handled")]
        ]
    )
