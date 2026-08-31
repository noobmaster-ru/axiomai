"""Аутентификация Telegram Mini App через initData.

Клиент передаёт строку initData из window.Telegram.WebApp.initData в заголовке
`Authorization: tma <initData>`. Подпись проверяется по алгоритму Telegram:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Annotated
from urllib.parse import parse_qsl

from fastapi import Depends, HTTPException, Request

from axiomai.config import Config

logger = logging.getLogger(__name__)

INIT_DATA_MAX_AGE_SECONDS = 24 * 60 * 60
AUTH_SCHEME = "tma"


class InitDataError(ValueError):
    """initData отсутствует, подделана или устарела."""


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = INIT_DATA_MAX_AGE_SECONDS,
    now: float | None = None,
) -> int:
    """Проверяет подпись initData и возвращает telegram_id пользователя."""
    data = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = data.pop("hash", None)
    if not received_hash:
        raise InitDataError("initData has no hash")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise InitDataError("initData signature mismatch")

    try:
        auth_date = int(data.get("auth_date", ""))
    except ValueError as exc:
        raise InitDataError("initData has no valid auth_date") from exc
    if (now or time.time()) - auth_date > max_age_seconds:
        raise InitDataError("initData is expired")

    try:
        user_id = json.loads(data["user"])["id"]
    except (KeyError, ValueError, TypeError) as exc:
        raise InitDataError("initData has no user id") from exc
    if not isinstance(user_id, int):
        raise InitDataError("initData user id is not an int")
    return user_id


async def authenticated_telegram_id(request: Request) -> int:
    """FastAPI-dependency: telegram_id пользователя из проверенной initData.

    Результат кэшируется FastAPI в рамках запроса, поэтому dependency можно
    вешать и на роутер (гейт), и в хендлере (значение) без двойной проверки.
    """
    config: Config = await request.state.dishka_container.get(Config)

    authorization = request.headers.get("Authorization", "")
    scheme, _, init_data = authorization.partition(" ")

    if not init_data and config.api_auth_dev_telegram_id is not None:
        return config.api_auth_dev_telegram_id

    if scheme.lower() != AUTH_SCHEME or not init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram init data")

    try:
        return validate_init_data(init_data, config.bot_token)
    except InitDataError as exc:
        logger.warning("rejected API request: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid Telegram init data") from exc


AuthenticatedTelegramId = Annotated[int, Depends(authenticated_telegram_id)]
