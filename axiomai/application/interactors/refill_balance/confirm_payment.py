import logging

from aiogram import Bot

from axiomai.application.exceptions.cabinet import CabinetNotFoundError
from axiomai.application.exceptions.payment import (
    PaymentAlreadyProcessedError,
    PaymentNotFoundError,
)
from axiomai.application.interactors.payment_common import ensure_refill_balance_payment
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.payment import PaymentGateway
from axiomai.infrastructure.database.gateways.user import UserGateway
from axiomai.infrastructure.database.models.payment import PaymentStatus
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.telegram.keyboards.reply import get_kb_menu

logger = logging.getLogger(__name__)


class ConfirmRefillBalancePayment:
    def __init__(
        self,
        tm: TransactionManager,
        payment_gateway: PaymentGateway,
        cabinet_gateway: CabinetGateway,
        user_gateway: UserGateway,
        bot: Bot,
    ) -> None:
        self._tm = tm
        self._payment_gateway = payment_gateway
        self._cabinet_gateway = cabinet_gateway
        self._user_gateway = user_gateway
        self._bot = bot

    async def execute(self, admin_telegram_id: int, payment_id: int) -> None:
        payment = await self._payment_gateway.get_payment_by_id(payment_id)
        if not payment:
            raise PaymentNotFoundError(f"Payment with id {payment_id} not found")

        ensure_refill_balance_payment(payment_id, payment.service_data)

        cabinet_id = payment.service_data.get("service_id")
        cabinet = await self._cabinet_gateway.get_cabinet_by_id(cabinet_id) if cabinet_id else None
        if not cabinet:
            raise CabinetNotFoundError(f"Cabinet.id = {cabinet_id} not found for the confirm payment")

        transitioned = await self._payment_gateway.transition_status(
            payment_id, PaymentStatus.WAITING_CONFIRM, PaymentStatus.SUCCEEDED
        )
        if not transitioned:
            raise PaymentAlreadyProcessedError(
                f"Payment with id = {payment_id} has already been processed (status: {payment.status.value})"
            )

        await self._cabinet_gateway.add_refill_balance(cabinet.id, payment.amount)

        await self._tm.commit()

        logger.info("refill balance payment %s confirmed by admin %s", payment_id, admin_telegram_id)

        user = await self._user_gateway.get_user_by_id(payment.user_id)
        if user and user.telegram_id:
            text = (
                f"✅ Оплата {payment_id} подтверждена.\n\n"
                f"На ваш баланс начислено {payment.amount} ₽.\n"
                "Теперь боту снова можно принимать заявки от клиентов."
            )
            await self._bot.send_message(chat_id=user.telegram_id, text=text, reply_markup=get_kb_menu(cabinet))
