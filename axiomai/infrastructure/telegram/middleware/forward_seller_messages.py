import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)


class ForwardSellerMessagesMiddleware(BaseMiddleware):
    def __init__(self, admin_telegram_ids: list[int], owner_telegram_id: int) -> None:
        self._admin_telegram_ids = admin_telegram_ids
        self._owner_telegram_id = owner_telegram_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
            # Only forward messages from non-admin sellers
            if user.id not in self._admin_telegram_ids and user.id != self._owner_telegram_id:
                bot: Bot = data["bot"]
                username = f"@{user.username}" if user.username else "(без username)"
                header = f"👤 <b>{username}</b> | ID: <code>{user.id}</code>\n\n"
                try:
                    if event.text:
                        await bot.send_message(
                            chat_id=self._owner_telegram_id,
                            text=header + event.text,
                        )
                    elif event.caption:
                        await bot.send_message(
                            chat_id=self._owner_telegram_id,
                            text=header + event.caption,
                        )
                    else:
                        await bot.send_message(
                            chat_id=self._owner_telegram_id,
                            text=header + "[медиа без текста]",
                        )
                except Exception:
                    logger.exception("Failed to forward message from seller %s to owner", user.id)

        return await handler(event, data)
