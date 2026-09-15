"""E2e-тесты HTTP API: аутентификация initData и проверка владения buyer'ом."""

from unittest.mock import AsyncMock

import pytest
from dishka.integrations.fastapi import setup_dishka
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from axiomai.api.auth import authenticated_telegram_id
from axiomai.api.routes.articles import router as articles_router
from axiomai.api.routes.buyers import router as buyers_router
from axiomai.infrastructure.database.models import Buyer
from axiomai.infrastructure.database.models.payment import Payment  # noqa: F401
from axiomai.infrastructure.superbanking import Superbanking
from tests.test_api_auth import BOT_TOKEN, make_init_data


@pytest.fixture
async def api_client(di_container):
    config = await di_container.get(__import__("axiomai.config", fromlist=["Config"]).Config)
    config.bot_token = BOT_TOKEN
    config.api_auth_dev_telegram_id = None

    app = FastAPI()
    auth_gate = [Depends(authenticated_telegram_id)]
    app.include_router(articles_router, dependencies=auth_gate)
    app.include_router(buyers_router, dependencies=auth_gate)
    setup_dishka(di_container, app)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


def _auth(telegram_id: int) -> dict[str, str]:
    return {"Authorization": f"tma {make_init_data(user_id=telegram_id)}"}


async def _make_buyer(session, cabinet_factory, telegram_id: int, amount: int | None = 200) -> Buyer:
    cabinet = await cabinet_factory(balance=1000, is_superbanking_connect=True)
    buyer = Buyer(
        cabinet_id=cabinet.id,
        username="api_user",
        fullname="Api User",
        telegram_id=telegram_id,
        nm_id=777,
        amount=amount,
        cashback_percent=100,
        phone_number=None,
        bank=None,
    )
    session.add(buyer)
    await session.flush()
    return buyer


async def test_articles_requires_auth(api_client):
    response = await api_client.get("/articles")
    assert response.status_code == 401


async def test_articles_with_valid_auth(api_client):
    response = await api_client.get("/articles", headers=_auth(111))
    assert response.status_code == 200
    assert response.json() == []


async def test_get_own_buyer(api_client, session, cabinet_factory):
    buyer = await _make_buyer(session, cabinet_factory, telegram_id=111)
    response = await api_client.get(f"/buyers/{buyer.id}", headers=_auth(111))
    assert response.status_code == 200
    assert response.json()["telegram_id"] == 111


async def test_foreign_buyer_returns_404(api_client, session, cabinet_factory):
    """Чужой buyer неотличим от несуществующего"""
    buyer = await _make_buyer(session, cabinet_factory, telegram_id=111)

    assert (await api_client.get(f"/buyers/{buyer.id}", headers=_auth(999))).status_code == 404
    assert (
        await api_client.post(f"/buyers/{buyer.id}/screenshots/order", headers=_auth(999))
    ).status_code == 404
    complete = await api_client.post(
        f"/buyers/{buyer.id}/complete",
        headers=_auth(999),
        json={"phone_number": "+7 910 111 22 33", "bank": "Тинькофф"},
    )
    assert complete.status_code == 404


async def test_complete_ignores_client_amount(api_client, session, di_container, cabinet_factory):
    """Сумма выплаты берётся из buyer.amount, назначенного селлером, а не из тела запроса"""
    buyer = await _make_buyer(session, cabinet_factory, telegram_id=222, amount=200)
    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = AsyncMock(return_value="tx-api")
    superbanking.sign_payment = AsyncMock(return_value=True)

    response = await api_client.post(
        f"/buyers/{buyer.id}/complete",
        headers=_auth(222),
        json={"phone_number": "+7 910 111 22 33", "bank": "Тинькофф", "amount": 999999},
    )

    assert response.status_code == 201
    assert superbanking.create_payment.await_args.kwargs["amount"] != 999999


async def test_screenshot_marks_own_buyer(api_client, session, cabinet_factory):
    buyer = await _make_buyer(session, cabinet_factory, telegram_id=333)
    response = await api_client.post(f"/buyers/{buyer.id}/screenshots/order", headers=_auth(333))
    assert response.status_code == 200
    await session.refresh(buyer)
    assert buyer.is_ordered is True
