"""Гейтвей к AI-моделям через kie.ai (OpenAI-совместимый Chat Completions API).

kie.ai — реселлер: endpoint `{KIE_BASE_URL}/chat/completions` принимает стандартный
формат messages/choices, поэтому клиентом служит официальный openai SDK с другим base_url.
Особенность vision: изображения передаются только внешними URL, поэтому base64 data URL
от хендлеров сначала загружается через File Upload API kie.ai (временное хранение ~3 дня).
"""

import json
import logging
import re
from contextlib import suppress
from typing import Any, TypedDict

import httpx
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from axiomai.config import KieConfig
from axiomai.constants import (
    GPT_MAX_OUTPUT_TOKENS,
    GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS,
    GPT_REASONING,
    KIE_BASE_URL,
    KIE_FILE_UPLOAD_URL,
    MODEL_NAME,
)
from axiomai.infrastructure.database.models import Buyer
from axiomai.infrastructure.database.models.cashback_table import CashbackArticle

logger = logging.getLogger(__name__)


class ChatHistoryEntry(TypedDict):
    user: str
    assistant: str


class OrderItem(TypedDict):
    nm_id: int
    price: int | None


class ClassifyOrderResult(TypedDict):
    is_order: bool
    orders: list[OrderItem]
    cancel_reason: str | None


class ClassifyFeedbackResult(TypedDict):
    is_feedback: bool
    nm_ids: list[int]
    cancel_reason: str | None


class ClassifyCutLabelsResult(TypedDict):
    is_cut_labels: bool
    cancel_reason: str | None


class AnswerResult(TypedDict):
    response: str
    wants_to_stop: bool
    wants_manager: bool
    switch_to_article_id: int | None


class PredialogResult(TypedDict):
    response: str
    article_ids: list[int]
    wants_manager: bool


class KieUploadError(Exception):
    """Не удалось загрузить изображение в файловое хранилище kie.ai."""


def _text(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def _image(url: str) -> dict[str, Any]:
    return {"type": "image_url", "image_url": {"url": url}}


class KieGateway:
    def __init__(self, config: KieConfig) -> None:
        self._api_key = config.kie_api_key
        self._client = AsyncOpenAI(
            api_key=config.kie_api_key,
            base_url=KIE_BASE_URL,
            # без явного timeout SDK ждёт ответ до 600 секунд
            timeout=httpx.Timeout(300.0, connect=5.0),
            max_retries=2,
        )
        # Отдельный клиент для File Upload API (не OpenAI-совместимая часть kie.ai)
        self._upload_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0))

    async def _upload_photo(self, photo_data_url: str) -> str:
        """Меняет base64 data URL на внешний URL: chat-endpoint kie.ai принимает только URL."""
        if photo_data_url.startswith(("http://", "https://")):
            return photo_data_url

        response = await self._upload_client.post(
            KIE_FILE_UPLOAD_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"base64Data": photo_data_url, "uploadPath": "axiomai/screenshots"},
        )
        if response.status_code != httpx.codes.OK:
            raise KieUploadError(f"kie.ai file upload failed: status={response.status_code}, body={response.text[:300]}")

        payload = response.json()
        download_url = (payload.get("data") or {}).get("downloadUrl")
        if not payload.get("success") or not download_url:
            raise KieUploadError(f"kie.ai file upload returned no downloadUrl: {str(payload)[:300]}")
        return download_url

    async def _create_completion(
        self,
        operation: str,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int,
        reasoning_effort: str,
    ) -> str | None:
        response = await self._client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,  # type: ignore[arg-type]
        )
        _log_response_usage(operation, response)
        return _extract_response_text(response)

    async def classify_order_screenshot(
        self,
        photo_data_url: str,
        articles: list[CashbackArticle],
    ) -> ClassifyOrderResult:
        """Классифицирует скриншот заказа по списку товаров."""
        articles_text = "\n".join(
            f'- nm_id={art.nm_id}, Название: "{art.title}", Бренд: "{art.brand_name}"'
            for art in articles
        )
        first_instruction = articles[0].instruction_text if articles else None
        valid_nm_ids = {art.nm_id for art in articles}

        system_content = """
        Ты помощник для анализа скриншотов заказов Wildberries.

        Проанализируй скриншот заказа на Wildberries и определи:
        1. Есть ли на скриншоте ЗАКАЗ одного или нескольких целевых товаров (из списка ниже)
        2. Какие именно товары заказаны (по nm_id) — на скриншоте может быть несколько заказов сразу
        3. Какая цена указана для каждого товара в рублях (₽)

        ВАЖНЫЕ признаки заказа на Wildberries:
        - Наличие слова "Заказы" в верхней части экрана
        - Рядом с карточкой товара есть статусы: "Оформляется", "Вы оформили заказ", "Оплачен" (зелёным), "НЕ ОПЛАЧЕН" (красным)
        - Карточка товара содержит изображение, название товара, бренд и цену

        Сравни изображение товара на скриншоте с эталонными изображениями товаров (если предоставлены).

        Верни ответ в формате JSON: {"is_order": bool, "orders": [{"nm_id": int, "price": int|null}], "cancel_reason": str|null}
        Где:
        - is_order = true, если заказ одного или нескольких наших товаров присутствует на скриншоте
        - orders = список найденных заказов наших товаров (может быть несколько, если на скриншоте видно несколько заказов)
        - каждый элемент: nm_id = артикул товара, price = цена в рублях или null если не видна
        - cancel_reason = причина отказа, если is_order = false
        """

        prompt = f"""
        ЦЕЛЕВЫЕ ТОВАРЫ (ищем заказы ОДНОГО ИЛИ НЕСКОЛЬКИХ из них):
        {articles_text}

        ИНСТРУКЦИЯ (дополнительные критерии для проверки):
        {first_instruction}
        """

        photo_url = await self._upload_photo(photo_data_url)
        user_content = [_text(prompt), _image(photo_url)]
        for art in articles:
            if art.image_url:
                user_content.append(_image(art.image_url))

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        result = await self._create_completion(
            "classify_order_screenshot",
            messages,
            max_tokens=GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS,
            reasoning_effort=GPT_REASONING,
        )

        if not result:
            return {"is_order": False, "orders": [], "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            parsed = json.loads(result)
            logger.debug("classified order screenshot %s", parsed)
            if parsed.get("orders"):
                parsed["orders"] = [o for o in parsed["orders"] if o.get("nm_id") in valid_nm_ids]
            if not parsed.get("orders"):
                parsed["orders"] = []
                parsed["is_order"] = False
            return parsed

        return {"is_order": False, "orders": [], "cancel_reason": None}

    async def classify_feedback_screenshot(
        self,
        photo_data_url: str,
        articles: list[CashbackArticle],
    ) -> ClassifyFeedbackResult:
        """Классифицирует скриншот отзыва по списку товаров."""
        articles_text = "\n".join(
            f'- nm_id={art.nm_id}, Название: "{art.title}", Бренд: "{art.brand_name}"'
            for art in articles
        )
        first_instruction = articles[0].instruction_text if articles else None
        valid_nm_ids = {art.nm_id for art in articles}

        system_content = """
        Ты помощник для анализа скриншотов отзывов Wildberries.

        Проанализируй скриншот и определи:
        1. Есть ли на скриншоте ОТЗЫВ на один или несколько целевых товаров (из списка ниже)
        2. На какие именно товары оставлены отзывы (по nm_id) — на скриншоте может быть несколько отзывов

        КРИТЕРИИ:
            - Подпись у товара должна быть названием целевого товара или его брендом.
            - На скриншоте клиента обязательно должны быть 5 оранжевых звёзд ⭐.
            - ТЕКСТ у отзыва может отсутствовать.
            - ТЕКСТ отзыва(ЕСЛИ ОН ЕСТь) НЕ должен содержать описание товара. Только общие фразы МОГУТ БЫТЬ, например: "товар хороший", "всё хорошо", "отличный товар", и тд
            - На скриншоте НЕ должно быть замазок/блюра и других изменений, только обычный скриншот с телефона без исправлений
            - Если на скриншоте есть пометки, что отзыв нарушет правила, или что отзыв не опубликован, нужно принять его

        Верни ответ в формате JSON: {"is_feedback": bool, "nm_ids": [int], "cancel_reason": str|null}
        Где:
        - is_feedback = true, если на скриншоте есть отзыв с 5 звёздами на один или несколько наших товаров (даже с нарушением правил)
        - nm_ids = список артикулов товаров, на которые оставлены отзывы (может быть несколько)
        - cancel_reason = причина отказа, если is_feedback = false
        """

        prompt = f"""
        Подумай и скажи есть ли на скриншоте ОТЗЫВ на один из наших товаров на Wildberries, сделанный согласно нашим КРИТЕРИЯМ.

        ЦЕЛЕВЫЕ ТОВАРЫ (ищем отзывы на ОДИН ИЛИ НЕСКОЛЬКО из них):
        {articles_text}

        ИНСТРУКЦИЯ (дополнительные критерии для проверки):
        {first_instruction}
        """

        photo_url = await self._upload_photo(photo_data_url)
        user_content = [_text(prompt), _image(photo_url)]
        for art in articles:
            if art.image_url:
                user_content.append(_image(art.image_url))

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        result = await self._create_completion(
            "classify_feedback_screenshot",
            messages,
            max_tokens=GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS,
            reasoning_effort=GPT_REASONING,
        )

        if not result:
            return {"is_feedback": False, "nm_ids": [], "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            parsed = json.loads(result)
            logger.info("classified feedback screenshot %s", parsed)
            if parsed.get("nm_ids"):
                parsed["nm_ids"] = [nid for nid in parsed["nm_ids"] if nid in valid_nm_ids]
            if not parsed.get("nm_ids"):
                parsed["nm_ids"] = []
                parsed["is_feedback"] = False
            return parsed

        return {"is_feedback": False, "nm_ids": [], "cancel_reason": None}

    async def classify_cut_labels_photo(
        self,
        photo_data_url: str,
        articles: list[CashbackArticle] | None = None,
    ) -> ClassifyCutLabelsResult:
        first_instruction = articles[0].instruction_text if articles else None

        system_content = """
        Ты помощник для анализа фотографий разрезанных этикеток Wildberries.

        Верни ответ в формате JSON: {{"is_cut_labels": bool, "cancel_reason": str|null}}
        Где:
        - is_cut_labels = true, если на фотографии есть РАЗРЕЗАННЫЕ/ПОРВАННЫЕ/ЗАМАЗАННЫЕ этикетки (штрихкода или QR-кода) Wildberries,
        - cancel_reason = причина отказа, если is_cut_labels = false
        """
        prompt = f"""
        Подумай и скажи есть ли на фотографии клиента РАЗРЕЗАННЫЕ/ПОРВАННЫЕ/ЗАМАЗАННЫЕ этикетки (штрихкода или QR-кода) Wildberries.

        ИНСТРУКЦИЯ (дополнительные критерии для проверки):
        {first_instruction}
        """

        photo_url = await self._upload_photo(photo_data_url)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": [_text(prompt), _image(photo_url)]},
        ]

        result = await self._create_completion(
            "classify_cut_labels_photo",
            messages,
            max_tokens=GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS,
            reasoning_effort=GPT_REASONING,
        )

        if not result:
            return {"is_cut_labels": False, "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            parsed = json.loads(result)
            logger.info("classified cut labels screenshot %s", parsed)
            return parsed

        return {"is_cut_labels": False, "cancel_reason": None}

    async def answer_user_question(
        self,
        user_message: str,
        articles: list[CashbackArticle],
        current_buyers: list[Buyer],
    ) -> AnswerResult:
        """Отвечает на вопрос пользователя в контексте кешбек-диалога."""
        articles_text = "\n".join([f"- ID:{article.id} Артикул WB: {article.nm_id}, Название: {article.title}" for article in articles])
        current_buyers_text = "\n".join(
            [
                f"- Артикул WB:{buyer.nm_id}, Скриншот заказа:{buyer.is_ordered} Скриншот отзыва:{buyer.is_left_feedback} Фото разрезанных этикеток:{buyer.is_left_feedback}"
                for buyer in current_buyers
            ]
        )

        instruction_text = articles[0].instruction_text

        system_content = """
        Ты — вежливый помощник кешбек-сервиса Wildberries.

        Процесс получения кешбека:
        1. Скриншот заказа — клиент отправляет скриншот оформленного заказа
        2. Скриншот отзыва — после получения товара клиент оставляет отзыв на 5 звёзд и присылает скриншот
        3. Фото разрезанных этикеток — клиент разрезает этикетки со штрихкодом/QR-кодом и присылает фото
        4. Реквизиты — клиент отправляет данные для перевода кешбека

        ВАЖНО:
        - Ответь кратко, по делу (не более 3-4 предложений) без смайликов и эмодзи
        - НЕ добавляй завершающие фразы типа "Если возникнут вопросы — помогу"
        - Используй разметку Markdown
        - НИКОГДА не показывай пользователю ID артикулов — только названия товаров
        - Если клиент спрашивает какие товары доступны — перечисли ТОЛЬКО названия из блока `articles_list` ниже.
        - Если клиент спрашивает фото или артикул товара или как ему найти товар, НЕ ГОВОРИ, что товар можно найти поиском по названию, переспроси,
           о каком товаре он спрашивает и перечисли ТОЛЬКО названия из блока `articles_list`
        - Если клиент спрашивает на каком он этапе или что ему нужно сделать, перечисли заявки из блока `buyers_list`

        СПЕЦИАЛЬНЫЕ КОМАНДЫ (добавляй в начало ответа если нужно):

        1. Если клиент ОДНОЗНАЧНО хочет прекратить процесс по текущему товару
           (например: "Не хочу", "Отмена", "Стоп", "Передумал", "Нет, спасибо", "Спасибо пока не нужно", "Спасибо, не надо","Не надо спасибо"),
           напиши [STOP] в начале ответа.

        2. Если пишет оскорбления, унижения, ругательства
           (например: "Пошел ты", "иди нахуй", "блять"),
           напиши [STOP] в начале ответа.

        3. Если клиент просит связаться с живым человеком, менеджером или оператором
           (например: "Позовите менеджера", "Хочу поговорить с человеком", "Оператор", "Менеджер", "Человек", "Живой оператор", "Свяжите с менеджером"),
           напиши [MANAGER] в начале ответа.

        4. Если пользователь просит начать оформление или упоминает товар,
           (например: "Давайте следующие пакеты", "Хочу ещё ролик", "Оформим диски", "Продолжаем, ножницы", "У меня же еще ножницы")
           которого НЕТ в `buyers_list`, но он ЕСТЬ в `articles_list`, ты должен начать ответ со специальной команды.
           напиши [SWITCH:ID] где ID — числовой идентификатор из `articles_list`.
           Пример: [SWITCH:123] Отлично, давайте оформим заявку на этот товар (БЕЗ упоминания ID после команды).

        Не путай вопросы или сомнения с командами — только явные намерения.
        """

        prompt = f"""
        ИНСТРУКЦИЯ, что и как нужно делать клиенту
        (МОЖЕШЬ  КРАТКО ПЕРЕСКАЗАТЬ КЛИЕНТУ, ЕСЛИ ОН НЕ ПОНИМАЕТ ЧТО ДЕЛАТЬ):
        {instruction_text}

        ДОСТУПНЫЕ ТОВАРЫ (`articles_list`):
        {articles_text}

        ТЕКУЩИЕ ЗАЯВКИ (`buyers_list`):
        {current_buyers_text}

        Новое сообщение клиента: "{user_message}"
        """

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ]

        # У kie.ai reasoning_effort по умолчанию "high" — для чат-ответов явно просим "low",
        # иначе бюджет max_tokens уйдёт на рассуждения, а ответ станет медленнее и дороже
        result = await self._create_completion(
            "answer_user_question",
            messages,
            max_tokens=GPT_MAX_OUTPUT_TOKENS,
            reasoning_effort="low",
        )
        return _parse_answer_result(result)

    async def chat_with_client(
        self,
        user_message: str,
        articles: list[CashbackArticle],
        chat_history: list[ChatHistoryEntry] | None = None,
        photo_data_url: str | None = None,
    ) -> PredialogResult:
        """Ведёт pre-dialog общение с клиентом до классификации артикула."""
        articles_info = "\n".join(f"- ID:{article.id} | Название: {article.title}" for article in articles)
        articles_titles = "\n".join(f"- {article.title}" for article in articles)
        valid_ids = {article.id for article in articles}

        history_text = ""
        if chat_history:
            history_lines = []
            for entry in chat_history[-10:]:
                history_lines.append(f"Клиент: {entry['user']}")
                history_lines.append(f"Ты: {entry['assistant']}")
            history_text = "\n".join(history_lines)

        # во тут вообще без понятия как в промпт передать конктретную инструкцию, поэтому передаю самую первую
        instructions = []
        for article in articles:
            instructions.append(article.instruction_text)
        first_instruction_text = instructions[0]

        system_content = """
        Ты — приветливый менеджер кешбек-сервиса на Wildberries. Твоя задача — помочь клиенту выбрать товар для кешбека.

        СТРОГИЕ ЗАПРЕТЫ:
        - НИКОГДА не давай ссылки на изображения или URL
        - НИКОГДА не угадывай товар — если непонятно, переспроси
        - НИКОГДА не показывай ID артикулов
        - НИКОГДА не придумывай информацию о товаре
        - НИКОГДА не говори пользователю как найти товар на маркетплейсе

        ПРАВИЛА ОБЩЕНИЯ:
        1. Отвечай кратко , по-деловому и четко (2-4 предложения) без смайликов и эмодзи
        2. Используй разметку Markdown
        3. НЕ добавляй формальные завершающие фразы

        ЛОГИКА ДИАЛОГА:
        - Если клиент просто здоровается или спрашивает "актуально?" — напиши "Напишите название товара, по которому хотите кэшбек" и перечисли доступные товары(БЕЗ ПРИЛАТЕЛЬНЫХ В НАЗВАНИИ ТОВАРА)
        - Если клиент спрашивает об условиях в общем — кратко скажи, что условия зависят от товара, и попроси уточнить название
        - Если клиент задаёт неопределённый вопрос ("это какое?", "фото можно?", "а что это?") — ПЕРЕСПРОСИ о каком именно товаре он спрашивает
        - Если клиент ЯВНО называет конкретный товар (например "ролик", "губки", "носки", "салфетка") — подтвердить выбор товара и ДОБАВЬ в начало ответа: [ARTICLE:ID]
        - Добавляй [ARTICLE:ID] ТОЛЬКО когда клиент ОДНОЗНАЧНО выбрал товар
        - Если клиент выбрал несколько товаров то перечисли их так [ARTICLE:ID1,ID2,ID3]
        - Если клиент просит связаться с живым человеком, менеджером или оператором
          (например: "Позовите менеджера", "Хочу поговорить с человеком", "Оператор", "Менеджер", "Человек", "Живой оператор", "Свяжите с менеджером"),
          напиши [MANAGER] в начале ответа.

        ПРИМЕР 1 (неопределённый вопрос):
        Клиент: "это какое? фото можно?"
        Ответ: Уточните, пожалуйста, о каком товаре вы спрашиваете? У нас есть: Ролик , Губка, Салфетка

        ПРИМЕР 2 (явный выбор):
        Клиент: "ролик"
        Ответ: [ARTICLE:123]Отлично, заказывайте на сайте товар, артикул: [АРТИКУЛ_РОЛИКА_ИЗ_ARTICLE_TITLES]
        """

        prompt = f"""
        ИНСТРУКЦИЯ, что и как нужно делать клиенту
        (МОЖЕШЬ  КРАТКО ПЕРЕСКАЗАТЬ КЛИЕНТУ, ЕСЛИ ОН НЕ ПОНИМАЕТ ЧТО ДЕЛАТЬ):
        {first_instruction_text}

        Доступные товары для кешбека (ТОЛЬКО ДЛЯ СИСТЕМЫ, ID не показывать пользователю):
        {articles_info}

        Список товаров для показа пользователю:
        {articles_titles}
        (ПОКАЗЫВАЙ ТОЛЬКО НАЗВАНИЕ ТОВАРА, БЕЗ ПРИЛАГАТЕЛЬНЫХ, например: Диски ватные специальные -> Диски)

        {"История диалога:" + chr(10) + history_text if history_text else ""}

        Новое сообщение клиента: "{user_message}"
        """

        user_content: list[dict[str, Any]] | str
        if photo_data_url:
            photo_url = await self._upload_photo(photo_data_url)
            user_content = [_text(prompt), _image(photo_url)]
        else:
            user_content = prompt

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        result = await self._create_completion(
            "chat_with_client",
            messages,
            max_tokens=GPT_MAX_OUTPUT_TOKENS,
            reasoning_effort="low",
        )
        parsed = _parse_predialog_result(result)

        if parsed["article_ids"]:
            parsed["article_ids"] = [aid for aid in parsed["article_ids"] if aid in valid_ids]

        return parsed


def _extract_response_text(response: ChatCompletion) -> str | None:
    """Извлекает текст ответа из chat completion"""
    if not response.choices:
        return None
    content = response.choices[0].message.content
    if not content:
        return None
    return content.strip() or None


def _log_response_usage(operation: str, response: ChatCompletion) -> None:
    usage = getattr(response, "usage", None)
    if not usage:
        return

    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)
    cached_tokens = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", None)
    reasoning_tokens = getattr(getattr(usage, "completion_tokens_details", None), "reasoning_tokens", None)

    logger.info(
        "%s usage: prompt_tokens=%s, cached_tokens=%s, completion_tokens=%s, reasoning_tokens=%s, total_tokens=%s",
        operation,
        prompt_tokens,
        cached_tokens,
        completion_tokens,
        reasoning_tokens,
        total_tokens,
    )


def _parse_answer_result(result: str | None) -> AnswerResult:
    """Парсит результат ответа модели и извлекает специальные команды"""
    if not result:
        return {
            "response": "Пожалуйста, следуйте инструкциям на экране.",
            "wants_to_stop": False,
            "wants_manager": False,
            "switch_to_article_id": None,
        }

    wants_to_stop = result.startswith("[STOP]")
    if wants_to_stop:
        result = result.replace("[STOP]", "").strip()

    wants_manager = "[MANAGER]" in result
    if wants_manager:
        result = result.replace("[MANAGER]", "").strip()

    switch_to_article_id = None
    if "[SWITCH:" in result:
        match = re.search(r"\[SWITCH:(\d+)\]", result)
        if match:
            switch_to_article_id = int(match.group(1))
            result = re.sub(r"\[SWITCH:\d+\]", "", result).strip()

    return AnswerResult(
        response=result,
        wants_to_stop=wants_to_stop,
        wants_manager=wants_manager,
        switch_to_article_id=switch_to_article_id,
    )


def _parse_predialog_result(result: str | None) -> PredialogResult:
    """Парсит результат pre-dialog ответа модели и извлекает article_ids"""
    if not result:
        return PredialogResult(response="Напишите название товара, по которому хотите кэшбек", article_ids=[], wants_manager=False)

    wants_manager = "[MANAGER]" in result
    if wants_manager:
        result = result.replace("[MANAGER]", "").strip()

    article_ids: list[int] = []
    if "[ARTICLE:" in result:
        match = re.search(r"\[ARTICLE:([\d,]+)\]", result)
        if match:
            ids_str = match.group(1)
            article_ids = [int(id_str) for id_str in ids_str.split(",") if id_str]
            result = re.sub(r"\[ARTICLE:[\d,]+\]", "", result).strip()

    return PredialogResult(response=result, article_ids=article_ids, wants_manager=wants_manager)
