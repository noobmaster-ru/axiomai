from axiomai.application.interactors.payment_common import CancelPaymentBase, ensure_buy_leads_payment


class CancelBuyLeadsPayment(CancelPaymentBase):
    _log_label = "buy leads"

    def _ensure_payment_kind(self, payment_id: int, service_data: dict) -> None:
        ensure_buy_leads_payment(payment_id, service_data)
