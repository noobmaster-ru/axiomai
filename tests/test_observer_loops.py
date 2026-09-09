"""Устойчивость observer-циклов: ошибка одной итерации не убивает цикл."""

import asyncio
import contextlib
from unittest.mock import AsyncMock

from axiomai.observer.__main__ import _run_observer_loop


class _FakeRequestContainer:
    def __init__(self, interactor) -> None:
        self._interactor = interactor

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, _dependency: type):
        return self._interactor


class _FakeContainer:
    def __init__(self, interactor) -> None:
        self._interactor = interactor

    def __call__(self):
        return _FakeRequestContainer(self._interactor)


async def test_loop_survives_iteration_failure():
    interactor = AsyncMock()
    interactor.execute.side_effect = [RuntimeError("db down"), None, None]

    task = asyncio.create_task(_run_observer_loop(_FakeContainer(interactor), object, "test", interval_seconds=0))
    while interactor.execute.await_count < 3:  # noqa: ASYNC110
        await asyncio.sleep(0.01)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    assert interactor.execute.await_count >= 3  # цикл пережил RuntimeError первой итерации
