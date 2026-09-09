from axiomai.application.interactors.payment_common import MarkPaymentWaitingConfirmBase
from axiomai.infrastructure.database.models.cabinet import Cabinet
from axiomai.infrastructure.database.models.payment import Payment


class MarkBuyLeadsPaymentWaitingConfirm(MarkPaymentWaitingConfirmBase):
    _log_label = "buy leads"

    async def _resolve_cabinet(self, payment: Payment) -> Cabinet | None:
        return await self._cabinet_gateway.get_cabinet_by_cashback_table_id(payment.cashback_table_id)

    def _build_admin_text(self, payment: Payment, cabinet: Cabinet) -> str:
        return (
            f"💸 Новая оплата {payment.id}\n"
            f"Кабинет ID: {cabinet.id}\n"
            f"Лидов: {payment.service_data['leads']}\n"
            f"Сумма: {payment.amount} ₽\n\n"
            "Подтвердите, пожалуйста"
        )
