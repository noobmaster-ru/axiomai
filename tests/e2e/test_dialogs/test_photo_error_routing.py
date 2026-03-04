from unittest.mock import AsyncMock, Mock

from axiomai.infrastructure.database.models.cashback_table import CashbackTableStatus
from axiomai.infrastructure.openai import OpenAIGateway
from tests.e2e.test_dialogs.conftest import FakeBotClient, FakeBot

def _mock_order_error(openai_gateway, article, cancel_reason="Неверный скриншот заказа"):
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": False,
        "orders": [],
        "cancel_reason": cancel_reason,
    })


def _mock_order_ok(openai_gateway, article):
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "orders": [{"nm_id": article.nm_id, "price": 1500}],
        "cancel_reason": None,
    })


def _mock_feedback_error(openai_gateway, cancel_reason="Неверный скриншот отзыва"):
    openai_gateway.classify_feedback_screenshot = AsyncMock(return_value={
        "is_feedback": False,
        "nm_ids": [],
        "cancel_reason": cancel_reason,
    })


def _mock_feedback_ok(openai_gateway, article):
    openai_gateway.classify_feedback_screenshot = AsyncMock(return_value={
        "is_feedback": True,
        "nm_ids": [article.nm_id],
        "cancel_reason": None,
    })


def _mock_labels_error(openai_gateway, cancel_reason="Неверное фото этикеток"):
    openai_gateway.classify_cut_labels_photo = AsyncMock(return_value={
        "is_cut_labels": False,
        "cancel_reason": cancel_reason,
    })


async def test_order_screenshot_first_error_sends_text_to_user(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.", "article_ids": [article.id], "wants_manager": False,
    })
    _mock_order_error(openai_gateway, article, cancel_reason="Неверный скриншот заказа")

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()

    assert any("Неверный скриншот заказа" in (m.text or "") for m in fake_bot.sent_messages)
    assert len(fake_bot.sent_photos) == 0


async def test_order_screenshot_second_error_sends_text_to_user(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.", "article_ids": [article.id], "wants_manager": False,
    })
    _mock_order_error(openai_gateway, article, cancel_reason="Неверный скриншот заказа")

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # 1st error
    await bot_client.send_business_photo()  # 2nd error

    error_messages = [m for m in fake_bot.sent_messages if "Неверный скриншот заказа" in (m.text or "")]
    assert len(error_messages) == 2
    assert len(fake_bot.sent_photos) == 0


async def test_order_screenshot_third_error_notifies_manager(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(
        business_connection_id=bot_client.business_connection_id,
        business_account_id=999999,
    )
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.", "article_ids": [article.id], "wants_manager": False,
    })
    _mock_order_error(openai_gateway, article, cancel_reason="Неверный скриншот заказа")

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # 1st error → text to user
    await bot_client.send_business_photo()  # 2nd error → text to user
    await bot_client.send_business_photo()  # 3rd error → manager notification

    assert len(fake_bot.sent_photos) == 1
    assert "ошибка со скрином заказа" in fake_bot.sent_photos[0].caption


async def test_order_screenshot_price_missing_first_error_sends_text_to_user(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.", "article_ids": [article.id], "wants_manager": False,
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "orders": [{"nm_id": article.nm_id, "price": None}],
        "cancel_reason": None,
    })

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()

    assert any("цену" in (m.text or "") for m in fake_bot.sent_messages)
    assert len(fake_bot.sent_photos) == 0


async def test_order_screenshot_price_missing_third_error_notifies_manager(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(
        business_connection_id=bot_client.business_connection_id,
        business_account_id=999999,
    )
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.", "article_ids": [article.id], "wants_manager": False,
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "orders": [{"nm_id": article.nm_id, "price": None}],
        "cancel_reason": None,
    })

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # 1st
    await bot_client.send_business_photo()  # 2nd
    await bot_client.send_business_photo()  # 3rd → manager

    assert len(fake_bot.sent_photos) == 1
    assert "не видно цену" in fake_bot.sent_photos[0].caption

async def test_feedback_screenshot_first_error_sends_text_to_user(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.", "article_ids": [article.id], "wants_manager": False,
    })
    _mock_order_ok(openai_gateway, article)
    _mock_feedback_error(openai_gateway, cancel_reason="Неверный скриншот отзыва")

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # order ok
    await bot_client.send_business_photo()  # feedback error #1

    assert any("Неверный скриншот отзыва" in (m.text or "") for m in fake_bot.sent_messages)
    assert len(fake_bot.sent_photos) == 0


async def test_feedback_screenshot_third_error_notifies_manager(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(
        business_connection_id=bot_client.business_connection_id,
        business_account_id=999999,
    )
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.", "article_ids": [article.id], "wants_manager": False,
    })
    _mock_order_ok(openai_gateway, article)
    _mock_feedback_error(openai_gateway, cancel_reason="Неверный скриншот отзыва")

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # order ok
    await bot_client.send_business_photo()  # feedback error #1
    await bot_client.send_business_photo()  # feedback error #2
    await bot_client.send_business_photo()  # feedback error #3 → manager

    assert len(fake_bot.sent_photos) == 1
    assert "ошибка со скрином отзыва" in fake_bot.sent_photos[0].caption

async def test_cut_labels_screenshot_first_error_sends_text_to_user(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.", "article_ids": [article.id], "wants_manager": False,
    })
    _mock_order_ok(openai_gateway, article)
    _mock_feedback_ok(openai_gateway, article)
    _mock_labels_error(openai_gateway, cancel_reason="Неверное фото этикеток")

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # order ok
    await bot_client.send_business_photo()  # feedback ok
    await bot_client.send_business_photo()  # labels error #1

    assert any("Неверное фото этикеток" in (m.text or "") for m in fake_bot.sent_messages)
    assert len(fake_bot.sent_photos) == 0


async def test_cut_labels_screenshot_third_error_notifies_manager(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id, business_account_id=999999)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.", "article_ids": [article.id], "wants_manager": False,
    })
    _mock_order_ok(openai_gateway, article)
    _mock_feedback_ok(openai_gateway, article)
    _mock_labels_error(openai_gateway, cancel_reason="Неверное фото этикеток")

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # order ok
    await bot_client.send_business_photo()  # feedback ok
    await bot_client.send_business_photo()  # labels error #1
    await bot_client.send_business_photo()  # labels error #2
    await bot_client.send_business_photo()  # labels error #3 → manager

    assert len(fake_bot.sent_photos) == 1
    assert "ошибка со скрином этикеток" in fake_bot.sent_photos[0].caption

