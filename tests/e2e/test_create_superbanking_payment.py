from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from aiogram import Bot
from aiohttp.web_exceptions import HTTPError
from sqlalchemy import select

from axiomai.application.exceptions.payment import NotEnoughBalanceError
from axiomai.application.exceptions.superbanking import CreatePaymentError
from axiomai.application.interactors.create_superbanking_payment import (
    CreateSuperbankingPayment,
    send_receipt_after_confirm,
)
from axiomai.constants import AXIOMAI_COMMISSION, SUPERBANKING_COMMISSION
from axiomai.infrastructure.database.models import Buyer, Cabinet
from axiomai.infrastructure.database.models.superbanking import SuperbankingPayout
from axiomai.infrastructure.superbanking import Superbanking


@pytest.fixture
async def create_superbanking_payment(di_container) -> CreateSuperbankingPayment:
    return await di_container.get(CreateSuperbankingPayment)


async def _create_buyer(
    session,
    cabinet_factory,
    *,
    phone_number=None,
    bank=None,
    amount=None,
    cabinet_balance: int = 0,
) -> tuple[Buyer, Cabinet]:
    cabinet = await cabinet_factory(balance=cabinet_balance, is_superbanking_connect=True)
    buyer = Buyer(
        cabinet_id=cabinet.id,
        username="test_user",
        fullname="Test User",
        telegram_id=123456,
        nm_id=777,
        phone_number=phone_number,
        bank=bank,
        amount=amount,
    )
    session.add(buyer)
    await session.flush()
    return buyer, cabinet


async def test_create_superbanking_payment_creates_payout(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    buyer, cabinet = await _create_buyer(session, cabinet_factory, amount=200, cabinet_balance=1000)
    superbanking = await di_container.get(Superbanking)

    # Override Superbanking mock with sync methods
    superbanking.create_payment = AsyncMock(return_value="tx-1")
    superbanking.sign_payment = AsyncMock(return_value=True)

    order_number = await create_superbanking_payment.execute(
        telegram_id=buyer.telegram_id,
        cabinet_id=buyer.cabinet_id,
        phone_number="+7 910 111 22 33",
        bank="Тинькофф",
        amount=200,
    )

    payout = await session.scalar(select(SuperbankingPayout).where(SuperbankingPayout.order_number == order_number))
    assert payout is not None
    assert payout.order_number == order_number


async def test_create_superbanking_payment_missing_bank_raises(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    buyer, cabinet = await _create_buyer(session, cabinet_factory, amount=200, cabinet_balance=1000)
    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = AsyncMock(side_effect=CreatePaymentError("Unknown bank"))
    superbanking.sign_payment = AsyncMock(return_value=True)

    with pytest.raises(CreatePaymentError):
        await create_superbanking_payment.execute(
            telegram_id=buyer.telegram_id,
            cabinet_id=buyer.cabinet_id,
            phone_number="+7 910 111 22 33",
            bank="Неизвестный банк",
            amount=200,
        )

    assert buyer.is_superbanking_paid is False
    assert cabinet.balance == 1000


async def test_create_superbanking_payment_distributes_amount_to_buyers_without_amount(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    cabinet = await cabinet_factory(balance=1000, is_superbanking_connect=True)
    buyer1 = Buyer(
        cabinet_id=cabinet.id,
        username="user1",
        fullname="User 1",
        telegram_id=123456,
        nm_id=111,
        amount=None,
    )
    buyer2 = Buyer(
        cabinet_id=cabinet.id,
        username="user2",
        fullname="User 2",
        telegram_id=123456,
        nm_id=222,
        amount=None,
    )
    session.add_all([buyer1, buyer2])
    await session.flush()

    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = AsyncMock(return_value="tx-1")
    superbanking.sign_payment = AsyncMock(return_value=True)

    await create_superbanking_payment.execute(
        telegram_id=123456,
        cabinet_id=cabinet.id,
        phone_number="+7 910 111 22 33",
        bank="Тинькофф",
        amount=400,
    )

    assert buyer1.amount == 200
    assert buyer2.amount == 200


async def test_create_superbanking_payment_does_not_override_existing_amounts(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    cabinet = await cabinet_factory(balance=1000, is_superbanking_connect=True)
    buyer1 = Buyer(
        cabinet_id=cabinet.id,
        username="user1",
        fullname="User 1",
        telegram_id=123456,
        nm_id=111,
        amount=100,
    )
    buyer2 = Buyer(
        cabinet_id=cabinet.id,
        username="user2",
        fullname="User 2",
        telegram_id=123456,
        nm_id=222,
        amount=300,
    )
    session.add_all([buyer1, buyer2])
    await session.flush()

    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = AsyncMock(return_value="tx-1")
    superbanking.sign_payment = AsyncMock(return_value=True)

    await create_superbanking_payment.execute(
        telegram_id=123456,
        cabinet_id=cabinet.id,
        phone_number="+7 910 111 22 33",
        bank="Тинькофф",
        amount=999,
    )

    assert buyer1.amount == 100
    assert buyer2.amount == 300


async def test_create_superbanking_payment_mixed_buyers_with_and_without_amount(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    cabinet = await cabinet_factory(balance=1000, is_superbanking_connect=True)
    buyer_with_amount = Buyer(
        cabinet_id=cabinet.id,
        username="user1",
        fullname="User 1",
        telegram_id=123456,
        nm_id=111,
        amount=150,
    )
    buyer_without_amount = Buyer(
        cabinet_id=cabinet.id,
        username="user2",
        fullname="User 2",
        telegram_id=123456,
        nm_id=222,
        amount=None,
    )
    session.add_all([buyer_with_amount, buyer_without_amount])
    await session.flush()

    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = AsyncMock(return_value="tx-1")
    superbanking.sign_payment = AsyncMock(return_value=True)

    await create_superbanking_payment.execute(
        telegram_id=123456,
        cabinet_id=cabinet.id,
        phone_number="+7 910 111 22 33",
        bank="Тинькофф",
        amount=400,
    )

    assert buyer_with_amount.amount == 150
    assert buyer_without_amount.amount == 200


async def test_create_superbanking_payment_raises_not_enough_balance(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    total_amount = 200
    total_charge = total_amount + SUPERBANKING_COMMISSION + AXIOMAI_COMMISSION
    buyer, cabinet = await _create_buyer(
        session, cabinet_factory, amount=total_amount, cabinet_balance=total_charge - 1
    )
    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = AsyncMock()
    superbanking.sign_payment = AsyncMock()

    with pytest.raises(NotEnoughBalanceError):
        await create_superbanking_payment.execute(
            telegram_id=buyer.telegram_id,
            cabinet_id=buyer.cabinet_id,
            phone_number="+7 910 111 22 33",
            bank="Тинькофф",
            amount=total_amount,
        )

    superbanking.create_payment.assert_not_called()
    assert cabinet.balance == total_charge - 1


async def test_create_superbanking_payment_succeeds_with_exact_balance(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    total_amount = 200
    total_charge = total_amount + SUPERBANKING_COMMISSION + AXIOMAI_COMMISSION
    buyer, cabinet = await _create_buyer(
        session, cabinet_factory, amount=total_amount, cabinet_balance=total_charge
    )
    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = AsyncMock(return_value="tx-exact")
    superbanking.sign_payment = AsyncMock(return_value=True)

    await create_superbanking_payment.execute(
        telegram_id=buyer.telegram_id,
        cabinet_id=buyer.cabinet_id,
        phone_number="+7 910 111 22 33",
        bank="Тинькофф",
        amount=total_amount,
    )

    assert cabinet.balance == total_charge  # balance is deducted asynchronously after payment confirmation


# --- Tests for send_receipt_after_confirm ---


@patch("axiomai.application.interactors.create_superbanking_payment.asyncio.sleep", new_callable=AsyncMock)
async def test_send_receipt_marks_buyers_paid_and_deducts_balance(
    mock_sleep, di_container, session, cabinet_factory
):
    cabinet = await cabinet_factory(
        balance=1000, is_superbanking_connect=True, business_connection_id="biz-1"
    )
    buyer = Buyer(
        cabinet_id=cabinet.id,
        username="test_user",
        fullname="Test User",
        telegram_id=123456,
        nm_id=777,
        amount=200,
    )
    session.add(buyer)
    await session.flush()

    superbanking = await di_container.get(Superbanking)
    superbanking.confirm_operation = AsyncMock(return_value="https://example.com/receipt.pdf")

    bot = await di_container.get(Bot)
    bot.send_document = AsyncMock()
    bot.send_message = AsyncMock()

    await send_receipt_after_confirm(
        di_container=di_container,
        telegram_id=123456,
        business_connection_id="biz-1",
        cabinet_id=cabinet.id,
        order_number="payment-test-1",
    )

    await session.refresh(buyer)
    await session.refresh(cabinet)

    assert buyer.is_superbanking_paid is True
    assert buyer.is_paid_manually is True
    assert cabinet.balance == 1000 - (200 + SUPERBANKING_COMMISSION + AXIOMAI_COMMISSION)

    superbanking.confirm_operation.assert_awaited_once_with(order_number="payment-test-1")
    bot.send_document.assert_awaited_once()
    bot.send_message.assert_awaited_once()


@patch("axiomai.application.interactors.create_superbanking_payment.asyncio.sleep", new_callable=AsyncMock)
async def test_send_receipt_multiple_buyers_all_marked_paid(
    mock_sleep, di_container, session, cabinet_factory
):
    cabinet = await cabinet_factory(
        balance=2000, is_superbanking_connect=True, business_connection_id="biz-2"
    )
    buyer1 = Buyer(
        cabinet_id=cabinet.id,
        username="user1",
        fullname="User 1",
        telegram_id=555,
        nm_id=111,
        amount=300,
    )
    buyer2 = Buyer(
        cabinet_id=cabinet.id,
        username="user2",
        fullname="User 2",
        telegram_id=555,
        nm_id=222,
        amount=400,
    )
    session.add_all([buyer1, buyer2])
    await session.flush()

    superbanking = await di_container.get(Superbanking)
    superbanking.confirm_operation = AsyncMock(return_value="https://example.com/receipt.pdf")

    bot = await di_container.get(Bot)
    bot.send_document = AsyncMock()
    bot.send_message = AsyncMock()

    await send_receipt_after_confirm(
        di_container=di_container,
        telegram_id=555,
        business_connection_id="biz-2",
        cabinet_id=cabinet.id,
        order_number="payment-test-2",
    )

    await session.refresh(buyer1)
    await session.refresh(buyer2)
    await session.refresh(cabinet)

    assert buyer1.is_superbanking_paid is True
    assert buyer1.is_paid_manually is True
    assert buyer2.is_superbanking_paid is True
    assert buyer2.is_paid_manually is True

    expected_charge = (300 + 400) + SUPERBANKING_COMMISSION + AXIOMAI_COMMISSION
    assert cabinet.balance == 2000 - expected_charge


@patch("axiomai.application.interactors.create_superbanking_payment.asyncio.sleep", new_callable=AsyncMock)
async def test_send_receipt_does_not_mark_buyers_when_confirm_fails(
    mock_sleep, di_container, session, cabinet_factory
):
    cabinet = await cabinet_factory(
        balance=1000, is_superbanking_connect=True, business_connection_id="biz-3"
    )
    buyer = Buyer(
        cabinet_id=cabinet.id,
        username="test_user",
        fullname="Test User",
        telegram_id=789,
        nm_id=777,
        amount=200,
    )
    session.add(buyer)
    await session.flush()

    superbanking = await di_container.get(Superbanking)
    superbanking.confirm_operation = AsyncMock(side_effect=ValueError("confirm failed"))

    bot = await di_container.get(Bot)
    bot.send_document = AsyncMock()
    bot.send_message = AsyncMock()

    await send_receipt_after_confirm(
        di_container=di_container,
        telegram_id=789,
        business_connection_id="biz-3",
        cabinet_id=cabinet.id,
        order_number="payment-fail",
    )

    await session.refresh(buyer)
    await session.refresh(cabinet)

    assert buyer.is_superbanking_paid is False
    assert cabinet.balance == 1000

    bot.send_document.assert_not_awaited()
    bot.send_message.assert_awaited_once()
    assert "позже" in bot.send_message.call_args[0][1]


@patch("axiomai.application.interactors.create_superbanking_payment.asyncio.sleep", new_callable=AsyncMock)
async def test_send_receipt_retries_on_transient_error_then_succeeds(
    mock_sleep, di_container, session, cabinet_factory
):
    cabinet = await cabinet_factory(
        balance=1000, is_superbanking_connect=True, business_connection_id="biz-4"
    )
    buyer = Buyer(
        cabinet_id=cabinet.id,
        username="test_user",
        fullname="Test User",
        telegram_id=321,
        nm_id=777,
        amount=200,
    )
    session.add(buyer)
    await session.flush()

    superbanking = await di_container.get(Superbanking)
    superbanking.confirm_operation = AsyncMock(
        side_effect=[ValueError("transient"), "https://example.com/receipt.pdf"]
    )

    bot = await di_container.get(Bot)
    bot.send_document = AsyncMock()
    bot.send_message = AsyncMock()

    await send_receipt_after_confirm(
        di_container=di_container,
        telegram_id=321,
        business_connection_id="biz-4",
        cabinet_id=cabinet.id,
        order_number="payment-retry",
    )

    await session.refresh(buyer)
    await session.refresh(cabinet)

    assert buyer.is_superbanking_paid is True
    assert buyer.is_paid_manually is True
    assert cabinet.balance == 1000 - (200 + SUPERBANKING_COMMISSION + AXIOMAI_COMMISSION)

    assert superbanking.confirm_operation.await_count == 2
    bot.send_document.assert_awaited_once()
