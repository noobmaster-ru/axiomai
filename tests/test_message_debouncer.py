import asyncio
import contextlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from redis.asyncio import Redis

from axiomai.config import MessageDebouncerConfig
from axiomai.infrastructure.message_debouncer import (
    MessageDebouncer,
    MessageData,
    merge_messages_text,
)


class TestMessageMerging:
    """Тесты объединения сообщений"""

    def test_merge_multiple_messages(self):
        """Объединение нескольких сообщений в один текст"""
        messages = [
            MessageData(text="Я по поводу", timestamp=1.0, message_id=1, has_photo=False),
            MessageData(text="ролика", timestamp=2.0, message_id=2, has_photo=False),
            MessageData(text="можно инструкцию", timestamp=3.0, message_id=3, has_photo=False),
        ]

        merged = merge_messages_text(messages)
        assert merged == "Я по поводу ролика можно инструкцию"

    def test_merge_messages_with_none(self):
        """Игнорирование None при объединении"""
        messages = [
            MessageData(text="Первое", timestamp=1.0, message_id=1, has_photo=False),
            MessageData(text=None, timestamp=2.0, message_id=2, has_photo=True),
            MessageData(text="Второе", timestamp=3.0, message_id=3, has_photo=False),
        ]

        merged = merge_messages_text(messages)
        assert merged == "Первое Второе"

    def test_merge_empty_messages(self):
        """Объединение пустых сообщений"""
        messages = [
            MessageData(text=None, timestamp=1.0, message_id=1, has_photo=True),
            MessageData(text="", timestamp=2.0, message_id=2, has_photo=False),
        ]

        merged = merge_messages_text(messages)
        assert merged == ""


async def test_immediate_processing_for_long_messages():
    """Длинные сообщения должны обрабатываться немедленно"""
    redis_mock = MagicMock(spec=Redis)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()

    debouncer = MessageDebouncer(redis=redis_mock, config=MessageDebouncerConfig(IMMEDIATE_PROCESSING_LENGTH=100))

    process_callback = AsyncMock()

    long_text = "a" * 150  # Сообщение длиннее порога
    message_data = MessageData(
        text=long_text,
        timestamp=datetime.now(timezone.utc).timestamp(),
        message_id=1,
        has_photo=False,
    )

    await debouncer.add_message(
        business_connection_id="biz_1",
        chat_id=100,
        message_data=message_data,
        process_callback=process_callback,
    )

    process_callback.assert_called_once()
    redis_mock.setex.assert_not_called()


class FakeRedis:
    """Минимальный in-memory Redis для тестов дебаунсера (TTL игнорируется)"""

    def __init__(self):
        self.storage: dict[str, str] = {}

    async def get(self, key):
        return self.storage.get(key)

    async def setex(self, key, ttl, value):
        self.storage[key] = value

    async def delete(self, key):
        self.storage.pop(key, None)


def _make_debouncer(**config_overrides):
    config = MessageDebouncerConfig(
        **{"MESSAGE_DEBOUNCE_DELAY": 1, "IMMEDIATE_PROCESSING_LENGTH": 100, **config_overrides}
    )
    return MessageDebouncer(redis=FakeRedis(), config=config)


def _msg(text, message_id):
    return MessageData(text=text, timestamp=1.0, message_id=message_id, has_photo=False)


async def test_concurrent_messages_are_not_lost():
    """Параллельные сообщения одного чата не затирают буфер друг друга"""
    debouncer = _make_debouncer()
    received: list[list[str]] = []

    async def callback(biz_id, chat_id, messages):
        received.append([m.text for m in messages])

    await asyncio.gather(
        *(
            debouncer.add_message(
                business_connection_id="biz_1", chat_id=1, message_data=_msg(f"msg-{i}", i), process_callback=callback
            )
            for i in range(5)
        )
    )
    timer = debouncer._active_timers["biz_1:1"]
    await timer

    assert len(received) == 1
    assert sorted(received[0]) == [f"msg-{i}" for i in range(5)]


async def test_immediate_processing_takes_buffer_and_cancels_timer():
    """Длинное сообщение забирает накопленный буфер: отложенный таймер не должен ответить второй раз"""
    debouncer = _make_debouncer()
    received: list[list[str]] = []

    async def callback(biz_id, chat_id, messages):
        received.append([m.text for m in messages])

    await debouncer.add_message(
        business_connection_id="biz_1", chat_id=1, message_data=_msg("короткое", 1), process_callback=callback
    )
    pending_timer = debouncer._active_timers["biz_1:1"]

    await debouncer.add_message(
        business_connection_id="biz_1", chat_id=1, message_data=_msg("б" * 150, 2), process_callback=callback
    )

    assert received == [["короткое", "б" * 150]]
    with contextlib.suppress(asyncio.CancelledError):
        await pending_timer  # даём отменённому таймеру доработать
    assert pending_timer.cancelled()
    assert debouncer.redis.storage == {}
    await asyncio.sleep(1.2)  # таймер не должен сработать вторым ответом
    assert len(received) == 1


async def test_timer_registry_is_cleaned_up_after_processing():
    """Записи в _active_timers не копятся после срабатывания таймера"""
    debouncer = _make_debouncer()

    async def callback(biz_id, chat_id, messages):
        pass

    for chat_id in range(3):
        await debouncer.add_message(
            business_connection_id="biz_1", chat_id=chat_id, message_data=_msg("привет", 1), process_callback=callback
        )

    await asyncio.gather(*debouncer._active_timers.values())
    assert debouncer._active_timers == {}
