"""Проверка прав сервис-аккаунта: отсутствие аккаунта в permissions — ошибка, а не молчаливый успех."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from axiomai.application.exceptions.cashback_table import WritePermissionError
from axiomai.infrastructure.google_sheets import GoogleSheetsGateway

SA_EMAIL = "axiomai@gserviceaccount.com"


def _make_gateway(permissions: list[dict]) -> GoogleSheetsGateway:
    gateway = GoogleSheetsGateway.__new__(GoogleSheetsGateway)  # обходим __init__ с чтением ключа
    gateway._service_account_email = SA_EMAIL
    gateway._discovered_apis = {}

    aiogoogle = MagicMock()
    aiogoogle.__aenter__ = AsyncMock(return_value=aiogoogle)
    aiogoogle.__aexit__ = AsyncMock(return_value=None)
    aiogoogle.discover = AsyncMock(return_value=MagicMock())
    aiogoogle.as_service_account = AsyncMock(return_value={"permissions": permissions})
    gateway._aiogoogle = aiogoogle
    return gateway


async def test_missing_service_account_raises_permission_error():
    gateway = _make_gateway(permissions=[{"emailAddress": "someone@else.com", "role": "owner"}])
    with pytest.raises(PermissionError, match="not present"):
        await gateway.ensure_service_account_added("table-1")


async def test_reader_role_raises_write_permission_error():
    gateway = _make_gateway(permissions=[{"emailAddress": SA_EMAIL, "role": "reader"}])
    with pytest.raises(WritePermissionError):
        await gateway.ensure_service_account_added("table-1")


async def test_writer_role_passes():
    gateway = _make_gateway(permissions=[{"emailAddress": SA_EMAIL, "role": "writer"}])
    await gateway.ensure_service_account_added("table-1")


async def test_discovery_is_cached():
    gateway = _make_gateway(permissions=[{"emailAddress": SA_EMAIL, "role": "writer"}])
    await gateway.ensure_service_account_added("table-1")
    await gateway.ensure_service_account_added("table-1")
    assert gateway._aiogoogle.discover.await_count == 1
