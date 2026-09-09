from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from axiomai.application.exceptions.superbanking import CreatePaymentError, SignPaymentError, SuperbankingRequestError
from axiomai.constants import URL_CONFIRM_PAYMENT, URL_SIGN_PAYMENT
from axiomai.config import SuperbankingConfig
from axiomai.infrastructure.superbanking import Superbanking


def _make_config() -> SuperbankingConfig:
    return SuperbankingConfig(
        **{
            "SUPERBANKING_API_KEY": "test-api-key",
            "SUPERBANKING_CABINET_ID": "cabinet-1",
            "SUPERBANKING_PROJECT_ID": "project-1",
            "SUPERBANKING_CLEARING_CENTER_ID": "clearing-1",
        }
    )


async def test_create_payment_success(monkeypatch: pytest.MonkeyPatch) -> None:
    superbanking = Superbanking(_make_config(), AsyncMock())
    captured: dict = {}

    async def fake_post_json(
        *,
        url: str,
        payload: dict,
        log_context: str,
        order_number: str | None = None,
        add_idempotency_token: bool = True,
    ) -> dict:
        captured["url"] = url
        captured["payload"] = payload
        captured["log_context"] = log_context
        captured["order_number"] = order_number
        captured["add_idempotency_token"] = add_idempotency_token
        return {"data": {"payout": {"id": 123}}}

    monkeypatch.setattr(superbanking, "_post_json", fake_post_json)

    order_number = "payment-1"
    cabinet_transaction_id = await superbanking.create_payment(
        phone_number="+7 (910) 111-22-33",
        bank_name_rus="Газпромбанк",
        amount=100,
        order_number=order_number,
    )

    assert cabinet_transaction_id == "123"
    assert captured["payload"]["cabinetId"] == "cabinet-1"
    assert captured["payload"]["projectId"] == "project-1"
    assert captured["payload"]["clearingCenterId"] == "clearing-1"
    assert captured["payload"]["orderNumber"] == order_number
    assert captured["order_number"] == order_number
    assert captured["payload"]["phone"].startswith("00")
    assert captured["payload"]["amount"] == 100
    assert captured["payload"]["bank"] == superbanking._get_bank_identifier_by_bank_name_rus("Газпромбанк")


async def test_create_payment_unknown_bank_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    superbanking = Superbanking(_make_config(), AsyncMock())

    async def fake_post_json(*args, **kwargs) -> dict:  # noqa: ANN001,ANN002,ANN003
        raise AssertionError("Should not call _post_json when bank is unknown")

    monkeypatch.setattr(superbanking, "_post_json", fake_post_json)

    with pytest.raises(CreatePaymentError, match="Unknown bank"):
        await superbanking.create_payment(
            phone_number="+7 910 111 22 33",
            bank_name_rus="Неизвестный банк",
            amount=100,
            order_number="payment-2",
        )


async def test_sign_payment_success(monkeypatch: pytest.MonkeyPatch) -> None:
    superbanking = Superbanking(_make_config(), AsyncMock())
    captured: dict = {}
    order_number = "payment-1"

    async def fake_post_json(
        *,
        url: str,
        payload: dict,
        log_context: str,
        order_number: str | None = None,
        add_idempotency_token: bool = True,
    ) -> dict:
        captured["payload"] = payload
        captured["order_number"] = order_number
        captured["add_idempotency_token"] = add_idempotency_token
        return {"result": True}

    monkeypatch.setattr(superbanking, "_post_json", fake_post_json)

    assert await superbanking.sign_payment("tx-1", order_number) is True
    assert captured["payload"]["cabinetId"] == "cabinet-1"
    assert captured["payload"]["cabinetTransactionId"] == "tx-1"
    assert captured["order_number"] == order_number
    assert captured["add_idempotency_token"] is True


async def test_sign_payment_invalid_result_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    superbanking = Superbanking(_make_config(), AsyncMock())
    order_number = "payment-2"

    async def fake_post_json(
        *,
        url: str,
        payload: dict,
        log_context: str,
        order_number: str | None = None,
        add_idempotency_token: bool = True,
    ) -> dict:
        return {"result": "not-bool"}

    monkeypatch.setattr(superbanking, "_post_json", fake_post_json)

    with pytest.raises(SignPaymentError):
        await superbanking.sign_payment("tx-2", order_number)


async def test_confirm_operation_success(monkeypatch: pytest.MonkeyPatch) -> None:
    superbanking = Superbanking(_make_config(), AsyncMock())
    captured: dict = {}

    async def fake_post_json(
        *,
        url: str,
        payload: dict,
        log_context: str,
        order_number: str | None = None,
        add_idempotency_token: bool = True,
    ) -> dict:
        captured["payload"] = payload
        captured["add_idempotency_token"] = add_idempotency_token
        return {"data": {"url": "https://example.com/receipt.pdf"}}

    monkeypatch.setattr(superbanking, "_post_json", fake_post_json)

    receipt_url = await superbanking.confirm_operation("payment-3")
    assert receipt_url == "https://example.com/receipt.pdf"
    assert captured["payload"]["cabinetId"] == "cabinet-1"
    assert captured["payload"]["orderNumber"] == "payment-3"
    assert captured["add_idempotency_token"] is False


async def test_confirm_operation_missing_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    superbanking = Superbanking(_make_config(), AsyncMock())

    async def fake_post_json(
        *,
        url: str,
        payload: dict,
        log_context: str,
        order_number: str | None = None,
        add_idempotency_token: bool = True,
    ) -> dict:
        return {"data": {}}

    monkeypatch.setattr(superbanking, "_post_json", fake_post_json)

    with pytest.raises(ValueError, match="Unexpected Superbanking confirm response"):
        await superbanking.confirm_operation("payment-4")


class _FakeResponse:
    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self._body = body

    async def text(self) -> str:
        return self._body

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


def _make_session(status: int | None = None, body: str = "", exc: Exception | None = None) -> MagicMock:
    session = MagicMock()
    if exc is not None:
        session.post = MagicMock(side_effect=exc)
    else:
        session.post = MagicMock(return_value=_FakeResponse(status, body))
    return session


async def test_post_json_raises_on_http_error() -> None:
    superbanking = Superbanking(_make_config(), _make_session(500, '{"error": "boom"}'))

    with pytest.raises(SuperbankingRequestError) as exc_info:
        await superbanking._post_json(url=URL_CONFIRM_PAYMENT, payload={}, log_context="confirm operation")

    assert exc_info.value.status == 500
    assert exc_info.value.body == '{"error": "boom"}'
    assert exc_info.value.is_retryable is True


async def test_post_json_client_error_is_not_retryable() -> None:
    superbanking = Superbanking(_make_config(), _make_session(400, '{"result": false}'))

    with pytest.raises(SuperbankingRequestError) as exc_info:
        await superbanking._post_json(url=URL_SIGN_PAYMENT, payload={}, log_context="sign payout")

    assert exc_info.value.status == 400
    assert exc_info.value.is_retryable is False


async def test_post_json_non_json_body_raises_request_error() -> None:
    superbanking = Superbanking(_make_config(), _make_session(200, "<html>bad gateway</html>"))

    with pytest.raises(SuperbankingRequestError) as exc_info:
        await superbanking._post_json(url=URL_CONFIRM_PAYMENT, payload={}, log_context="confirm operation")

    assert exc_info.value.status == 200
    assert "<html>" in (exc_info.value.body or "")


async def test_post_json_network_error_is_retryable() -> None:
    superbanking = Superbanking(_make_config(), _make_session(exc=aiohttp.ClientConnectionError("boom")))

    with pytest.raises(SuperbankingRequestError) as exc_info:
        await superbanking._post_json(url=URL_CONFIRM_PAYMENT, payload={}, log_context="confirm operation")

    assert exc_info.value.status is None
    assert exc_info.value.is_retryable is True
    assert isinstance(exc_info.value.__cause__, aiohttp.ClientConnectionError)


async def test_post_json_success_returns_parsed_body() -> None:
    superbanking = Superbanking(_make_config(), _make_session(200, '{"result": true}'))

    result = await superbanking._post_json(url=URL_SIGN_PAYMENT, payload={}, log_context="sign payout")

    assert result == {"result": True}
