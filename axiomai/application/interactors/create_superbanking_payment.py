import asyncio
import logging

from aiogram import Bot
from aiogram.types import URLInputFile
from aiohttp.web_exceptions import HTTPError
from dishka import AsyncContainer

from axiomai.application.exceptions.payment import NotEnoughBalanceError
from axiomai.application.exceptions.superbanking import CreatePaymentError, SignPaymentError, SkipSuperbankingError
from axiomai.constants import (
    AXIOMAI_COMMISSION,
    CONFIRM_PAYMENT_BACKOFF_BASE,
    CONFIRM_PAYMENT_MAX_RETRIES,
    SUPERBANKING_COMMISSION,
    TIME_SLEEP_BEFORE_CONFIRM_PAYMENT,
    WB_CHANNEL_NAME,
)
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.superbanking_payout import SuperbankingPayoutGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.superbanking import Superbanking

logger = logging.getLogger(__name__)


class CreateSuperbankingPayment:
    def __init__(
        self,
        buyer_gateway: BuyerGateway,
        cabinet_gateway: CabinetGateway,
        superbanking_payout_gateway: SuperbankingPayoutGateway,
        transaction_manager: TransactionManager,
        superbanking: Superbanking,
        di_container: AsyncContainer,
    ) -> None:
        self._buyer_gateway = buyer_gateway
        self._cabinet_gateway = cabinet_gateway
        self._superbanking_payout_gateway = superbanking_payout_gateway
        self._transaction_manager = transaction_manager
        self._superbanking = superbanking
        self._di_container = di_container

    async def execute(
        self,
        *,
        telegram_id: int,
        cabinet_id: int,
        phone_number: str,
        bank: str,
        amount: int | None
    ) -> str:
        cabinet = await self._cabinet_gateway.get_cabinet_by_id(cabinet_id)
        if not cabinet:
            raise ValueError(f"Cabinet with id {cabinet_id} not found")

        buyers = await self._buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(telegram_id, cabinet_id)

        nm_ids = []
        total_amount = 0

        part_amount = (amount or 0) // len(buyers)

        for buyer in buyers:
            buyer.phone_number = phone_number
            buyer.bank = bank

            if not buyer.amount:
                buyer.amount = part_amount

            nm_ids.append(buyer.nm_id)
            total_amount += buyer.amount

        await self._transaction_manager.commit()

        if not cabinet.is_superbanking_connect:
            logger.info(
                "CreateSuperbankingPayment saved requisites without Superbanking payout: cabinet_id=%s",
                cabinet.id,
            )
            await self._transaction_manager.commit()
            raise SkipSuperbankingError(cabinet_id=cabinet.id, is_superbanking_connect=cabinet.is_superbanking_connect)

        total_charge = total_amount + SUPERBANKING_COMMISSION + AXIOMAI_COMMISSION

        if cabinet.balance < total_charge:
            raise NotEnoughBalanceError

        order_number = self._superbanking_payout_gateway.build_order_number(
            telegram_id=telegram_id,
            nm_ids=nm_ids,
            phone_number=phone_number,
            bank=bank,
            amount=total_amount,
        )
        payout = await self._superbanking_payout_gateway.create_payout(
            telegram_id=telegram_id,
            nm_ids=nm_ids,
            phone_number=phone_number,
            bank=bank,
            amount=total_amount,
            order_number=order_number,
        )

        try:
            cabinet_transaction_id = await self._superbanking.create_payment(
                phone_number=phone_number,
                bank_name_rus=bank,
                amount=total_amount,
                order_number=payout.order_number,
            )
        except CreatePaymentError:
            logger.exception("Failed to create_payment() Superbanking payout for payout_id=%s", payout.id)
            raise

        try:
            await self._superbanking.sign_payment(cabinet_transaction_id=cabinet_transaction_id, order_number=payout.order_number)
        except SignPaymentError:
            logger.exception("Failed to sign_payment() Superbanking payout for payout_id=%s", payout.id)
            raise

        logger.info(
            "scheduling receipt check: telegram_id=%s, order_number=%s",
            telegram_id,
            order_number,
        )

        task = asyncio.create_task(
            send_receipt_after_confirm(
                di_container=self._di_container,
                telegram_id=telegram_id,
                business_connection_id=cabinet.business_connection_id,
                cabinet_id=cabinet_id,
                order_number=order_number,
            )
        )
        task.add_done_callback(lambda _: None)

        return payout.order_number


async def send_receipt_after_confirm(
    di_container: AsyncContainer,
    telegram_id: int,
    business_connection_id: str,
    cabinet_id: int,
    order_number: str,
) -> None:
    superbanking = await di_container.get(Superbanking)
    bot = await di_container.get(Bot)

    await asyncio.sleep(TIME_SLEEP_BEFORE_CONFIRM_PAYMENT)

    check_url: str | None = None
    last_exc: Exception | None = None
    for attempt in range(CONFIRM_PAYMENT_MAX_RETRIES):
        try:
            check_url = await superbanking.confirm_operation(order_number=order_number)
            break
        except (ValueError, HTTPError) as exc:
            last_exc = exc
            delay = CONFIRM_PAYMENT_BACKOFF_BASE * (2 ** attempt)
            logger.warning(
                "confirm_operation() attempt %d/%d failed for telegram_id=%s, retrying in %ds",
                attempt + 1,
                CONFIRM_PAYMENT_MAX_RETRIES,
                telegram_id,
                delay,
            )
            await asyncio.sleep(delay)

    if check_url is None:
        logger.exception(
            "Failed to confirm_operation() after %d attempts for telegram_id=%s",
            CONFIRM_PAYMENT_MAX_RETRIES,
            telegram_id,
            exc_info=last_exc,
        )
        await bot.send_message(
            telegram_id,
            "Чек будет доступен чуть позже. Мы пришлём его дополнительно.",
            business_connection_id=business_connection_id,
        )
        return

    pdf_file = URLInputFile(check_url, filename="Чек.pdf")
    await bot.send_document(
        telegram_id,
        document=pdf_file,
        caption="Чек по выплате",
        business_connection_id=business_connection_id,
    )

    async with di_container() as r_container:
        buyer_gateway = await r_container.get(BuyerGateway)
        cabinet_gateway = await r_container.get(CabinetGateway)
        transaction_manager = await r_container.get(TransactionManager)

        buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(telegram_id, cabinet_id)
        cabinet = await cabinet_gateway.get_cabinet_by_id(cabinet_id)

        if buyers and cabinet:
            total_amount = sum(b.amount for b in buyers if b.amount)
            total_charge = total_amount + SUPERBANKING_COMMISSION + AXIOMAI_COMMISSION
            for buyer in buyers:
                buyer.is_superbanking_paid = True
                buyer.is_paid_manually = True
            cabinet.balance -= total_charge
            await transaction_manager.commit()

    await bot.send_message(
        telegram_id,
        f"Подписывайтесь на наш канал {WB_CHANNEL_NAME}, там будет много интересных товаров с БОЛЬШИМ кэшбеком ☺",
        business_connection_id=business_connection_id,
    )
