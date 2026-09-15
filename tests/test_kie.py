"""Юниты на KieGateway: построение messages с data URL, парсеры маркеров."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from axiomai.config import KieConfig
from axiomai.infrastructure.kie import (
    KieGateway,
    _parse_answer_result,
    _parse_predialog_result,
    build_instruction_text,
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


def _mock_create(gateway: KieGateway, text: str | None) -> AsyncMock:
    create = AsyncMock(return_value=_completion(text))
    gateway._client = MagicMock(chat=MagicMock(completions=MagicMock(create=create)))
    return create


# --- построение messages ---


async def test_classify_order_sends_data_url_and_article_images():
    gateway = _make_gateway()
    create = _mock_create(gateway, '{"is_order": true, "orders": [{"nm_id": 777, "price": 250}], "cancel_reason": null}')

    result = await gateway.classify_order_screenshot(DATA_URL, [_make_article()])

    assert result["is_order"] is True
    assert result["orders"] == [{"nm_id": 777, "price": 250}]
    kwargs = create.await_args.kwargs
    user_content = kwargs["messages"][1]["content"]
    image_urls = [part["image_url"]["url"] for part in user_content if part["type"] == "image_url"]
    # первым идёт скриншот клиента (data URL без промежуточной загрузки), затем эталонное фото артикула
    assert image_urls == [DATA_URL, "https://wb.example.com/art.jpg"]
    assert kwargs["reasoning_effort"] == "high"
    assert kwargs["model"]


async def test_classify_order_filters_foreign_nm_ids():
    gateway = _make_gateway()
    _mock_create(gateway, '{"is_order": true, "orders": [{"nm_id": 999, "price": 100}], "cancel_reason": null}')

    result = await gateway.classify_order_screenshot(DATA_URL, [_make_article(nm_id=777)])

    assert result["is_order"] is False
    assert result["orders"] == []


async def test_classify_feedback_filters_foreign_nm_ids():
    gateway = _make_gateway()
    _mock_create(gateway, '{"is_feedback": true, "nm_ids": [999], "cancel_reason": null}')

    result = await gateway.classify_feedback_screenshot(DATA_URL, [_make_article(nm_id=777)])

    assert result["is_feedback"] is False
    assert result["nm_ids"] == []


async def test_chat_with_client_without_photo_sends_plain_text():
    gateway = _make_gateway()
    create = _mock_create(gateway, "[ARTICLE:1] Отлично, оформляем")

    result = await gateway.chat_with_client("ролик", [_make_article(article_id=1)])

    assert result["article_ids"] == [1]
    assert result["response"] == "Отлично, оформляем"
    assert isinstance(create.await_args.kwargs["messages"][1]["content"], str)
    assert create.await_args.kwargs["reasoning_effort"] == "low"


async def test_chat_with_client_with_photo_attaches_data_url():
    gateway = _make_gateway()
    create = _mock_create(gateway, "Вижу фото")

    await gateway.chat_with_client("что это?", [_make_article()], photo_data_url=DATA_URL)

    user_content = create.await_args.kwargs["messages"][1]["content"]
    assert {"type": "image_url", "image_url": {"url": DATA_URL}} in user_content


async def test_chat_with_client_filters_unknown_article_ids():
    gateway = _make_gateway()
    _mock_create(gateway, "[ARTICLE:1,42] Выбор сделан")

    result = await gateway.chat_with_client("ролик и губка", [_make_article(article_id=1)])

    assert result["article_ids"] == [1]


async def test_empty_completion_gives_safe_defaults():
    gateway = _make_gateway()
    _mock_create(gateway, None)

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


# --- инструкция из заявки (зафиксированная), а не из артикула ---


def _make_buyer(nm_id: int = 777, instruction_text: str = "Инструкция заявки") -> SimpleNamespace:
    return SimpleNamespace(
        nm_id=nm_id, instruction_text=instruction_text, is_ordered=True, is_left_feedback=False, is_cut_labels=False
    )


def _prompt_text(create: AsyncMock) -> str:
    content = create.await_args.kwargs["messages"][1]["content"]
    return content if isinstance(content, str) else content[0]["text"]


async def test_classify_order_prefers_buyer_instruction_over_current_article_instruction():
    gateway = _make_gateway()
    create = _mock_create(gateway, '{"is_order": false, "orders": [], "cancel_reason": null}')
    article = _make_article()
    article.instruction_text = "Текущая инструкция артикула"

    await gateway.classify_order_screenshot(DATA_URL, [article], instruction_text="Инструкция заявки")

    prompt = _prompt_text(create)
    assert "Инструкция заявки" in prompt
    assert "Текущая инструкция артикула" not in prompt


async def test_classify_feedback_and_cut_labels_accept_buyer_instruction():
    gateway = _make_gateway()
    create = _mock_create(gateway, '{"is_feedback": false, "nm_ids": [], "cancel_reason": null}')
    await gateway.classify_feedback_screenshot(DATA_URL, [_make_article()], instruction_text="Инструкция заявки")
    assert "Инструкция заявки" in _prompt_text(create)

    create = _mock_create(gateway, '{"is_cut_labels": true, "cancel_reason": null}')
    await gateway.classify_cut_labels_photo(DATA_URL, [_make_article()], instruction_text="Инструкция заявки")
    assert "Инструкция заявки" in _prompt_text(create)


async def test_classify_order_falls_back_to_article_instruction_without_buyer_instruction():
    gateway = _make_gateway()
    create = _mock_create(gateway, '{"is_order": false, "orders": [], "cancel_reason": null}')

    await gateway.classify_order_screenshot(DATA_URL, [_make_article()])

    assert "Инструкция" in _prompt_text(create)


async def test_answer_user_question_uses_buyer_instruction_and_survives_empty_articles():
    gateway = _make_gateway()
    create = _mock_create(gateway, "Отвечаю")

    # выбранный товар сняли с наличия → доступных артикулов нет; раньше это роняло ответ IndexError
    result = await gateway.answer_user_question("что делать?", articles=[], current_buyers=[_make_buyer()])

    assert result["response"] == "Отвечаю"
    assert "Инструкция заявки" in _prompt_text(create)


def test_build_instruction_text_single_shared_instruction():
    buyers = [_make_buyer(nm_id=1, instruction_text="Общая"), _make_buyer(nm_id=2, instruction_text="Общая")]
    assert build_instruction_text(buyers) == "Общая"


def test_build_instruction_text_labels_different_instructions_by_nm_id():
    buyers = [_make_buyer(nm_id=1, instruction_text="Первая"), _make_buyer(nm_id=2, instruction_text="Вторая")]
    text = build_instruction_text(buyers)
    assert "Для артикула 1:\nПервая" in text
    assert "Для артикула 2:\nВторая" in text


def test_build_instruction_text_empty_returns_none():
    assert build_instruction_text([]) is None
    assert build_instruction_text([_make_buyer(instruction_text="")]) is None
