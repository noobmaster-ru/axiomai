from axiomai.application.interactors.payment_common import CancelPaymentBase, ensure_refill_balance_payment


class CancelRefillBalancePayment(CancelPaymentBase):
    _log_label = "refill balance"

    def _ensure_payment_kind(self, payment_id: int, service_data: dict) -> None:
        ensure_refill_balance_payment(payment_id, service_data)
