"""Общая логика confirm/cancel/mark-waiting интеракторов платежей.

Здесь же живут проверки соответствия платежа типу операции: платёж buy_leads
не должен обрабатываться refill-интерактором и наоборот (их service_id
означают разные сущности).
"""

import logging

from aiogram import Bot

from axiomai.application.exceptions.cabinet import CabinetNotFoundError
from axiomai.application.exceptions.payment import (
    PaymentAlreadyProcessedError,
    PaymentNotFoundError,
    PaymentTypeMismatchError,
)
from axiomai.config import Config
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.payment import PaymentGateway
from axiomai.infrastructure.database.models.cabinet import Cabinet
from axiomai.infrastructure.database.models.payment import (
    SERVICE_DATA_TYPE_BUY_LEADS,
    SERVICE_DATA_TYPE_REFILL_BALANCE,
    Payment,
    PaymentStatus,
)
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.telegram.keyboards.inline import build_payment_admin_keyboard

logger = logging.getLogger(__name__)


def ensure_refill_balance_payment(payment_id: int, service_data: dict) -> None:
    """Платёж без type — легаси-пополнение; буст-платёж (type или "leads") сюда попадать не должен."""
    payment_type = service_data.get("type")
    if payment_type not in (None, SERVICE_DATA_TYPE_REFILL_BALANCE) or "leads" in service_data:
        raise PaymentTypeMismatchError(f"Payment {payment_id} is not a refill-balance payment (type={payment_type!r})")


def ensure_buy_leads_payment(payment_id: int, service_data: dict) -> None:
    payment_type = service_data.get("type")
    if payment_type != SERVICE_DATA_TYPE_BUY_LEADS:
        raise PaymentTypeMismatchError(f"Payment {payment_id} is not a buy-leads payment (type={payment_type!r})")


class CancelPaymentBase:
    """Отмена платежа админом: WAITING_CONFIRM -> CANCELED"""

    _log_label: str

    def __init__(self, tm: TransactionManager, payment_gateway: PaymentGateway) -> None:
        self._tm = tm
        self._payment_gateway = payment_gateway

    def _ensure_payment_kind(self, payment_id: int, service_data: dict) -> None:
        raise NotImplementedError

    async def execute(self, admin_telegram_id: int, payment_id: int, reason: str | None = None) -> None:
        payment = await self._payment_gateway.get_payment_by_id(payment_id)
        if not payment:
            raise PaymentNotFoundError(f"Payment with id = {payment_id} not found")

        self._ensure_payment_kind(payment_id, payment.service_data)

        transitioned = await self._payment_gateway.transition_status(
            payment_id, PaymentStatus.WAITING_CONFIRM, PaymentStatus.CANCELED
        )
        if not transitioned:
            raise PaymentAlreadyProcessedError(
                f"Payment with id = {payment_id} has already been processed (status: {payment.status.value})"
            )

        if reason:
            payment.canceled_reason = reason

        await self._tm.commit()

        logger.info("%s payment %s canceled by admin %s", self._log_label, payment_id, admin_telegram_id)


class MarkPaymentWaitingConfirmBase:
    """Перевод платежа в ожидание подтверждения (CREATED -> WAITING_CONFIRM) с уведомлением админа"""

    _log_label: str

    def __init__(
        self,
        tm: TransactionManager,
        payment_gateway: PaymentGateway,
        cabinet_gateway: CabinetGateway,
        config: Config,
        bot: Bot,
    ) -> None:
        self._tm = tm
        self._payment_gateway = payment_gateway
        self._cabinet_gateway = cabinet_gateway
        self._config = config
        self._bot = bot

    async def _resolve_cabinet(self, payment: Payment) -> Cabinet | None:
        raise NotImplementedError

    def _build_admin_text(self, payment: Payment, cabinet: Cabinet) -> str:
        raise NotImplementedError

    async def execute(self, payment_id: int) -> None:
        payment = await self._payment_gateway.get_payment_by_id(payment_id)
        if not payment:
            raise PaymentNotFoundError(f"Payment with id = {payment_id} not found")

        # Кабинет и текст резолвим ДО коммита: иначе ошибка ниже оставила бы платёж
        # в WAITING_CONFIRM без единого уведомления админу
        cabinet = await self._resolve_cabinet(payment)
        if not cabinet:
            raise CabinetNotFoundError(f"Cabinet not found for payment id = {payment_id} to mark waiting")
        text = self._build_admin_text(payment, cabinet)

        if payment.status != PaymentStatus.CREATED:
            raise PaymentAlreadyProcessedError(
                f"Payment with id = {payment_id} cannot be marked as waiting (status: {payment.status.value})"
            )

        payment.status = PaymentStatus.WAITING_CONFIRM

        await self._tm.commit()

        try:
            await self._bot.send_message(
                chat_id=self._config.admin_telegram_ids[0],
                text=text,
                reply_markup=build_payment_admin_keyboard(payment_id),
            )
        except Exception:
            # Сбой Telegram не должен выглядеть как сбой платежа — статус уже зафиксирован
            logger.exception("failed to notify admin about %s payment %s", self._log_label, payment_id)

        logger.info("%s payment %s marked as waiting confirmation", self._log_label, payment_id)
