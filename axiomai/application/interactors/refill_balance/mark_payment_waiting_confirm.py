from axiomai.application.interactors.payment_common import MarkPaymentWaitingConfirmBase
from axiomai.infrastructure.database.models.cabinet import Cabinet
from axiomai.infrastructure.database.models.payment import Payment


class MarkRefillBalancePaymentWaitingConfirm(MarkPaymentWaitingConfirmBase):
    _log_label = "refill balance"

    async def _resolve_cabinet(self, payment: Payment) -> Cabinet | None:
        cabinet_id = payment.service_data.get("service_id")
        return await self._cabinet_gateway.get_cabinet_by_id(cabinet_id) if cabinet_id else None

    def _build_admin_text(self, payment: Payment, cabinet: Cabinet) -> str:
        return (
            f"💸 Новое пополнение баланса {payment.id}\n"
            f"Кабинет ID: {cabinet.id}\n"
            f"Сумма: {payment.amount} ₽\n\n"
            "Подтвердите, пожалуйста"
        )
