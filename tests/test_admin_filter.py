"""IsAdminFilter: только пользователи из ADMIN_TELEGRAM_IDS проходят к платёжным колбэкам."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from axiomai.tgbot.filters.is_admin import IsAdminFilter
from axiomai.tgbot.handlers.admin_confirms import router


class _FakeContainer:
    def __init__(self, admin_ids: list[int]) -> None:
        self._config = MagicMock(admin_telegram_ids=admin_ids)

    async def get(self, _dependency: type):
        return self._config


def _event(user_id: int | None):
    return SimpleNamespace(from_user=SimpleNamespace(id=user_id) if user_id else None)


async def test_admin_passes():
    assert await IsAdminFilter()(_event(42), _FakeContainer([42, 43])) is True


async def test_non_admin_rejected():
    assert await IsAdminFilter()(_event(99), _FakeContainer([42, 43])) is False


async def test_event_without_user_rejected():
    assert await IsAdminFilter()(_event(None), _FakeContainer([42])) is False


def test_payment_callbacks_are_guarded_by_admin_filter():
    """admin_pay_ok / admin_pay_fail обязаны иметь IsAdminFilter в цепочке фильтров"""
    guarded = 0
    for handler in router.callback_query.handlers:
        filter_objects = [f.callback for f in handler.filters]
        if any(isinstance(f, IsAdminFilter) for f in filter_objects):
            guarded += 1
    assert guarded >= 2  # confirm + reject
