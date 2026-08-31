import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from axiomai.api.auth import AuthenticatedTelegramId, InitDataError, validate_init_data

BOT_TOKEN = "123456:test-bot-token"


def make_init_data(
    bot_token: str = BOT_TOKEN,
    user_id: int = 777,
    auth_date: int | None = None,
    *,
    tamper_hash: bool = False,
    drop_user: bool = False,
) -> str:
    fields = {
        "query_id": "AAF-test",
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
    }
    if not drop_user:
        fields["user"] = json.dumps({"id": user_id, "first_name": "Test"})

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    valid_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    fields["hash"] = "0" * 64 if tamper_hash else valid_hash
    return urlencode(fields)


def test_valid_init_data_returns_user_id() -> None:
    assert validate_init_data(make_init_data(user_id=42), BOT_TOKEN) == 42


def test_tampered_hash_rejected() -> None:
    with pytest.raises(InitDataError, match="signature"):
        validate_init_data(make_init_data(tamper_hash=True), BOT_TOKEN)


def test_wrong_bot_token_rejected() -> None:
    with pytest.raises(InitDataError, match="signature"):
        validate_init_data(make_init_data(bot_token="999:other-token"), BOT_TOKEN)


def test_expired_auth_date_rejected() -> None:
    stale = int(time.time()) - 25 * 60 * 60
    with pytest.raises(InitDataError, match="expired"):
        validate_init_data(make_init_data(auth_date=stale), BOT_TOKEN)


def test_missing_hash_rejected() -> None:
    with pytest.raises(InitDataError, match="hash"):
        validate_init_data("auth_date=1&user=%7B%22id%22%3A1%7D", BOT_TOKEN)


def test_missing_user_rejected() -> None:
    with pytest.raises(InitDataError, match="user"):
        validate_init_data(make_init_data(drop_user=True), BOT_TOKEN)


class _FakeConfig:
    bot_token = BOT_TOKEN
    api_auth_dev_telegram_id: int | None = None


class _FakeContainer:
    def __init__(self, config: _FakeConfig) -> None:
        self._config = config

    async def get(self, _dependency: type) -> _FakeConfig:
        return self._config


def make_client(config: _FakeConfig) -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def put_container(request: Request, call_next):
        request.state.dishka_container = _FakeContainer(config)
        return await call_next(request)

    @app.get("/me")
    async def me(telegram_id: AuthenticatedTelegramId) -> dict:
        return {"telegram_id": telegram_id}

    return TestClient(app)


def test_endpoint_accepts_valid_header() -> None:
    client = make_client(_FakeConfig())
    response = client.get("/me", headers={"Authorization": f"tma {make_init_data(user_id=555)}"})
    assert response.status_code == 200
    assert response.json() == {"telegram_id": 555}


def test_endpoint_rejects_missing_header() -> None:
    client = make_client(_FakeConfig())
    assert client.get("/me").status_code == 401


def test_endpoint_rejects_bad_scheme_and_forged_data() -> None:
    client = make_client(_FakeConfig())
    init_data = make_init_data()
    assert client.get("/me", headers={"Authorization": f"Bearer {init_data}"}).status_code == 401
    forged = make_init_data(tamper_hash=True)
    assert client.get("/me", headers={"Authorization": f"tma {forged}"}).status_code == 401


def test_dev_bypass_used_only_without_header() -> None:
    config = _FakeConfig()
    config.api_auth_dev_telegram_id = 111
    client = make_client(config)

    assert client.get("/me").json() == {"telegram_id": 111}
    # с заголовком проверка идёт по-настоящему, обход не применяется
    response = client.get("/me", headers={"Authorization": f"tma {make_init_data(user_id=555)}"})
    assert response.json() == {"telegram_id": 555}
    assert client.get("/me", headers={"Authorization": f"tma {make_init_data(tamper_hash=True)}"}).status_code == 401
