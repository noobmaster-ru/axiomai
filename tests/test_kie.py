"""Юниты на KieGateway: загрузка фото, построение messages, парсеры маркеров."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from axiomai.config import KieConfig
from axiomai.infrastructure.kie import (
    KieGateway,
    KieUploadError,
    _parse_answer_result,
    _parse_predialog_result,
)

DATA_URL = "data:image/jpeg;base64,/9j/AAAA"


def _make_gateway() -> KieGateway:
    return KieGateway(KieConfig(KIE_API_KEY="test-key"))


def _make_article(article_id: int = 1, nm_id: int = 777) -> SimpleNamespace:
    return SimpleNamespace(
        id=article_id,
        nm_id=nm_id,
        title="Ролик",
        brand_name="Brand",
        image_url="https://wb.example.com/art.jpg",
        instruction_text="Инструкция",
    )


def _completion(text: str | None) -> MagicMock:
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content=text))]
    completion.usage = None
    return completion


def _upload_response(status_code: int = 200, payload: dict | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = str(payload)
    response.json.return_value = payload or {}
    return response


# --- _upload_photo ---


async def test_upload_photo_returns_download_url():
    gateway = _make_gateway()
    gateway._upload_client.post = AsyncMock(
        return_value=_upload_response(
            payload={"success": True, "data": {"downloadUrl": "https://tempfile.example/img.jpg"}}
        )
    )

    url = await gateway._upload_photo(DATA_URL)

    assert url == "https://tempfile.example/img.jpg"
    sent = gateway._upload_client.post.await_args
    assert sent.kwargs["json"]["base64Data"] == DATA_URL
    assert sent.kwargs["headers"]["Authorization"] == "Bearer test-key"


async def test_upload_photo_skips_plain_urls():
    gateway = _make_gateway()
    gateway._upload_client.post = AsyncMock()

    url = await gateway._upload_photo("https://already.url/img.jpg")

    assert url == "https://already.url/img.jpg"
    gateway._upload_client.post.assert_not_awaited()


async def test_upload_photo_raises_on_http_error():
    gateway = _make_gateway()
    gateway._upload_client.post = AsyncMock(return_value=_upload_response(status_code=500, payload={}))

    with pytest.raises(KieUploadError):
        await gateway._upload_photo(DATA_URL)


async def test_upload_photo_raises_without_download_url():
    gateway = _make_gateway()
    gateway._upload_client.post = AsyncMock(return_value=_upload_response(payload={"success": True, "data": {}}))

    with pytest.raises(KieUploadError):
        await gateway._upload_photo(DATA_URL)


# --- messages: фото уходит внешним URL, картинки артикулов добавляются ---


async def test_classify_order_uploads_photo_and_builds_chat_messages():
    gateway = _make_gateway()
    gateway._upload_client.post = AsyncMock(
        return_value=_upload_response(payload={"success": True, "data": {"downloadUrl": "https://tempfile.example/x.jpg"}})
    )
    create = AsyncMock(return_value=_completion('{"is_order": true, "orders": [{"nm_id": 777, "price": 250}], "cancel_reason": null}'))
    gateway._client = MagicMock(chat=MagicMock(completions=MagicMock(create=create)))

    result = await gateway.classify_order_screenshot(DATA_URL, [_make_article()])

    assert result["is_order"] is True
    assert result["orders"] == [{"nm_id": 777, "price": 250}]
    kwargs = create.await_args.kwargs
    user_content = kwargs["messages"][1]["content"]
    image_urls = [part["image_url"]["url"] for part in user_content if part["type"] == "image_url"]
    # первым идёт загруженный скриншот, затем эталонное фото артикула
    assert image_urls == ["https://tempfile.example/x.jpg", "https://wb.example.com/art.jpg"]
    assert kwargs["reasoning_effort"] == "high"


async def test_classify_order_filters_foreign_nm_ids():
    gateway = _make_gateway()
    gateway._upload_photo = AsyncMock(return_value="https://tempfile.example/x.jpg")
    create = AsyncMock(return_value=_completion('{"is_order": true, "orders": [{"nm_id": 999, "price": 100}], "cancel_reason": null}'))
    gateway._client = MagicMock(chat=MagicMock(completions=MagicMock(create=create)))

    result = await gateway.classify_order_screenshot(DATA_URL, [_make_article(nm_id=777)])

    assert result["is_order"] is False
    assert result["orders"] == []


async def test_chat_with_client_without_photo_sends_plain_text():
    gateway = _make_gateway()
    gateway._upload_photo = AsyncMock()
    create = AsyncMock(return_value=_completion("[ARTICLE:1] Отлично, оформляем"))
    gateway._client = MagicMock(chat=MagicMock(completions=MagicMock(create=create)))

    result = await gateway.chat_with_client("ролик", [_make_article(article_id=1)])

    assert result["article_ids"] == [1]
    assert result["response"] == "Отлично, оформляем"
    gateway._upload_photo.assert_not_awaited()
    assert isinstance(create.await_args.kwargs["messages"][1]["content"], str)


async def test_chat_with_client_filters_unknown_article_ids():
    gateway = _make_gateway()
    create = AsyncMock(return_value=_completion("[ARTICLE:1,42] Выбор сделан"))
    gateway._client = MagicMock(chat=MagicMock(completions=MagicMock(create=create)))

    result = await gateway.chat_with_client("ролик и губка", [_make_article(article_id=1)])

    assert result["article_ids"] == [1]


async def test_empty_completion_gives_safe_defaults():
    gateway = _make_gateway()
    gateway._upload_photo = AsyncMock(return_value="https://tempfile.example/x.jpg")
    create = AsyncMock(return_value=_completion(None))
    gateway._client = MagicMock(chat=MagicMock(completions=MagicMock(create=create)))

    result = await gateway.classify_cut_labels_photo(DATA_URL, [_make_article()])

    assert result == {"is_cut_labels": False, "cancel_reason": None}


# --- парсеры маркеров ---


def test_parse_answer_stop():
    parsed = _parse_answer_result("[STOP] Хорошо, останавливаемся")
    assert parsed["wants_to_stop"] is True
    assert parsed["response"] == "Хорошо, останавливаемся"


def test_parse_answer_manager_and_switch():
    parsed = _parse_answer_result("[MANAGER] Зову менеджера")
    assert parsed["wants_manager"] is True

    parsed = _parse_answer_result("[SWITCH:123] Переключаемся на другой товар")
    assert parsed["switch_to_article_id"] == 123
    assert parsed["response"] == "Переключаемся на другой товар"


def test_parse_answer_empty_returns_fallback_text():
    parsed = _parse_answer_result(None)
    assert parsed["wants_to_stop"] is False
    assert parsed["response"]


def test_parse_predialog_multiple_articles():
    parsed = _parse_predialog_result("[ARTICLE:1,2,3] Оформляем всё")
    assert parsed["article_ids"] == [1, 2, 3]
    assert parsed["response"] == "Оформляем всё"


def test_parse_predialog_manager():
    parsed = _parse_predialog_result("[MANAGER] Секунду")
    assert parsed["wants_manager"] is True
    assert parsed["article_ids"] == []
