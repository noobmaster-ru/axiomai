from sqlalchemy import select, update

from axiomai.infrastructure.database.gateways.base import Gateway
from axiomai.infrastructure.database.models import Payment
from axiomai.infrastructure.database.models.payment import PaymentStatus


class PaymentGateway(Gateway):
    async def create_payment(self, payment: Payment) -> None:
        self._session.add(payment)
        await self._session.flush()

    async def get_payment_by_id(self, payment_id: int) -> Payment | None:
        return await self._session.scalar(select(Payment).where(Payment.id == payment_id))

    async def transition_status(self, payment_id: int, from_status: PaymentStatus, to_status: PaymentStatus) -> bool:
        """Атомарный переход статуса: False, если платёж уже не в from_status
        (например, второй админ успел обработать его параллельно).
        """
        result = await self._session.execute(
            update(Payment)
            .where(Payment.id == payment_id, Payment.status == from_status)
            .values(status=to_status)
        )
        return result.rowcount == 1
