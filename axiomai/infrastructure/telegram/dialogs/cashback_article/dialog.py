from typing import Any

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import DefaultKeyBuilder, StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Const, Format, Jinja
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from redis.asyncio import Redis

from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.telegram.dialogs.cashback_article.common import (
    get_pending_nm_ids_for_step,
    mes_input_handler,
)
from axiomai.infrastructure.telegram.dialogs.cashback_article.q1_input_order_screenshot import on_input_order_screenshot
from axiomai.infrastructure.telegram.dialogs.cashback_article.q2_input_feedback_screenshot import (
    on_input_feedback_screenshot,
)
from axiomai.infrastructure.telegram.dialogs.cashback_article.q3_input_cut_labels_screenshot import (
    on_input_cut_labels_photo,
)
from axiomai.infrastructure.telegram.dialogs.cashback_article.q4_input_requisites import (
    on_confirm_requisites,
    on_decline_requisites,
    on_input_requisites,
)
from axiomai.infrastructure.telegram.dialogs.states import CashbackArticleStates


@inject
async def article_getter(
    dialog_manager: DialogManager,
    cabinet_gateway: FromDishka[CabinetGateway],
    buyer_gateway: FromDishka[BuyerGateway],
    cashback_table_gateway: FromDishka[CashbackTableGateway],
    **kwargs: dict[str, Any],
) -> dict[str, Any]:
    if isinstance(dialog_manager.event, CallbackQuery):
        business_connection_id = dialog_manager.event.message.business_connection_id
    else:
        business_connection_id = dialog_manager.event.business_connection_id

    cabinet = await cabinet_gateway.get_cabinet_by_business_connection_id(business_connection_id)
    buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(dialog_manager.event.from_user.id, cabinet.id)

    pending_order_nm_ids = get_pending_nm_ids_for_step(buyers, "check_order")
    pending_feedback_nm_ids = get_pending_nm_ids_for_step(buyers, "check_received")
    pending_labels_nm_ids = get_pending_nm_ids_for_step(buyers, "check_labels_cut")

    pending_order =  await cashback_table_gateway.get_cashback_articles_by_nm_ids(pending_order_nm_ids)
    pending_feedback = await cashback_table_gateway.get_cashback_articles_by_nm_ids(pending_feedback_nm_ids)
    pending_labels = await cashback_table_gateway.get_cashback_articles_by_nm_ids(pending_labels_nm_ids)

    buyer_map = {b.nm_id: b for b in buyers if not b.is_ordered}
    cancellable_buyers = [
        buyer_map[a.nm_id]
        for a in pending_order
        if a.nm_id in buyer_map
    ]

    all_cabinet_buyers = await buyer_gateway.get_buyers_by_cabinet_id(cabinet.id)
    show_no_text_reminder = len(all_cabinet_buyers) % 5 == 0

    return {
        "peding_order": pending_order,
        "pending_feedback": pending_feedback,
        "pending_labels": pending_labels,
        "cancellable_buyers": cancellable_buyers,
        "show_no_text_reminder": show_no_text_reminder,
    }


@inject
async def requisites_getter(
    dialog_manager: DialogManager,
    cabinet_gateway: FromDishka[CabinetGateway],
    buyer_gateway: FromDishka[BuyerGateway],
    **kwargs: dict[str, Any],
) -> dict[str, Any]:
    cabinet = await cabinet_gateway.get_cabinet_by_business_connection_id(dialog_manager.event.business_connection_id)
    buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(dialog_manager.event.from_user.id, cabinet.id)

    # Суммируем amount по всем завершённым заявкам (с фото этикеток)
    total_amount = sum(b.amount or 0 for b in buyers if b.is_cut_labels)
    completed_buyers = [b for b in buyers if b.is_cut_labels]
    
    # Формируем текст со списком товаров и их суммами
    items_text = ""
    if len(completed_buyers) > 1:
        items_lines = [f"• {b.nm_id} — {b.amount or '?'} ₽" for b in completed_buyers]
        items_text = "\n".join(items_lines)
    
    return {
        "amount": dialog_manager.dialog_data.get("amount") or total_amount or None,
        "phone_number": dialog_manager.dialog_data.get("phone_number"),
        "bank": dialog_manager.dialog_data.get("bank"),
        "total_amount": total_amount or None,
        "items_text": items_text,
        "buyers_count": len(completed_buyers),
    }


@inject
async def on_close(
    _: dict[str, Any], dialog_manager: DialogManager, bot: FromDishka[Bot], redis: FromDishka[Redis]
) -> None:
    if isinstance(dialog_manager.event, CallbackQuery):
        business_connection_id = dialog_manager.event.message.business_connection_id
    else:
        business_connection_id = dialog_manager.event.business_connection_id

    state = FSMContext(
        RedisStorage(redis, key_builder=DefaultKeyBuilder(with_destiny=True, with_business_connection_id=True)),
        StorageKey(
            user_id=dialog_manager.event.from_user.id,
            chat_id=dialog_manager.event.from_user.id,
            bot_id=bot.id,
            business_connection_id=business_connection_id,
        ),
    )

    await state.clear()


ORDER_INPUT_TEXT = """
Отправьте, пожалуйста, <b>скриншоты</b> сделанного заказа следующих артикулов:
{% for pending in peding_order %}
• <code>{{ pending.nm_id }}</code> — {{ pending.title }}
{% endfor %}
"""

FEEDBACK_INPUT_TEXT = """
📬 Когда получите товары, отправьте, пожалуйста, <b>скриншот отзыва</b> на 5 звёзд следующих артикулов:
{% for pending in pending_feedback %}
• <code>{{ pending.nm_id }}</code> — {{ pending.title }}
{% endfor %}
{% if show_no_text_reminder %}
⚠️ <b>Важно:</b> оставьте отзыв <u>без текста</u> — только звёзды, без описания!
{% else %}
⚠️ <b>Важно:</b> оставьте отзыв <u>без фото/видео</u>, а также <u>без упоминания товара</u>!
{% endif %}"""

CUT_LABELS_INPUT_TEXT = """
✂ Разрежте этикетки (qr-код или штрихкод) и отправьте, пожалуйста, фотографию разрезанных этикеток для следующих артикулов:
{% for pending in pending_labels %}
• <code>{{ pending.nm_id }}</code> — {{ pending.title }}
{% endfor %}
"""


cashback_article_dialog = Dialog(
    Window(
        Jinja(ORDER_INPUT_TEXT),
        MessageInput(on_input_order_screenshot, content_types=[ContentType.PHOTO]),
        MessageInput(mes_input_handler),
        state=CashbackArticleStates.check_order,
        getter=article_getter,
    ),
    Window(
        Jinja(FEEDBACK_INPUT_TEXT),
        MessageInput(on_input_feedback_screenshot, content_types=[ContentType.PHOTO]),
        MessageInput(mes_input_handler),
        state=CashbackArticleStates.check_received,
        getter=article_getter,
    ),
    Window(
        Jinja(CUT_LABELS_INPUT_TEXT),
        MessageInput(on_input_cut_labels_photo, content_types=[ContentType.PHOTO]),
        MessageInput(mes_input_handler),
        state=CashbackArticleStates.check_labels_cut,
        getter=article_getter,
    ),
    Window(
        Const(
            "Отправьте теперь нам, пожалуйста, свой номер телефона в формате:\n\n<code>+7910XXXXXXX</code>",
            # когда нет номера телефона, суммы и банка
            when=lambda d, _, __: not any((d["phone_number"], d["amount"], d["bank"])),
        ),
        Const(
            "📩 Получены реквизиты:",
            # когда есть хотя бы один из: номер телефона, сумма или банк
            when=lambda d, _, __: any((d["phone_number"], d["amount"], d["bank"])),
        ),
        Format("Номер телефона: <code>{phone_number}</code>", when=lambda d, _, __: d["phone_number"]),
        Format("Банк: <code>{bank}</code>", when=lambda d, _, __: d["bank"]),
        Format(
            "\n<b>Товары к выплате:</b>\n{items_text}",
            when=lambda d, _, __: d.get("items_text"),
        ),
        Format(
            "Итого к выплате: <code>{total_amount} ₽</code>",
            when=lambda d, _, __: d.get("buyers_count", 0) > 1 and d.get("total_amount"),
        ),
        Format(
            "Сумма: <code>{amount} ₽</code>",
            when=lambda d, _, __: d["amount"] and d.get("buyers_count", 1) <= 1,
        ),
        Const(" "),
        Const(
            "💬 Пожалуйста, отправьте название банка (например: <b>Сбербанк</b>, <b>Т-банк</b>)",
            # когда нет банка и есть сумма, или номер телефона
            when=lambda d, _, __: (not d["bank"]) and (d["amount"] or d["phone_number"]),
        ),
        Const(
            "💬 Пожалуйста, отправьте реквизиты для оплаты: номер телефона.",
            # когда нет номера телефона и есть банк или сумма
            when=lambda d, _, __: (not d["phone_number"]) and (d["bank"] or d["amount"]),
        ),
        Const(
            "💬 Пожалуйста, отправьте сумму перевода, например: 160 рублей",
            # когда нет суммы и есть банк или номер телефона
            when=lambda d, _, __: (not d["amount"]) and (d["bank"] or d["phone_number"]),
        ),
        Const(
            "Реквизиты заполнены верно?",
            # когда есть все реквизиты: номер телефона, сумма, банк
            when=lambda d, _, __: all((d["phone_number"] , d["amount"], d["bank"])),
        ),
        Row(
            Button(
                Const("✅ Да, верно"),
                id="conf_requisites",
                on_click=on_confirm_requisites,
                when=lambda d, _, __: all((d["phone_number"], d["amount"], d["bank"])),
            ),
            Button(
                Const("❌ Не верно"),
                id="dec_requisites",
                on_click=on_decline_requisites,
                when=lambda d, _, __: all((d["phone_number"], d["amount"], d["bank"])),
            ),
        ),
        MessageInput(on_input_requisites),
        state=CashbackArticleStates.input_requisites,
        getter=requisites_getter,
    ),
    on_close=on_close,
)
