import base64
import io
import logging
import re

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


async def mark_business_message_read(
    bot: Bot, business_connection_id: str, chat_id: int, message_id: int
) -> None:
    """Помечает входящее сообщение прочитанным.

    Вызывается непосредственно перед отправкой ответа, а не в момент получения, чтобы
    прочтение не выглядело для клиента мгновенным. Ошибка прочтения (например, у бота
    отозвано право «Read messages») не должна ломать отправку ответа.
    """
    try:
        await bot.read_business_message(business_connection_id, chat_id, message_id)
    except TelegramAPIError:
        logger.warning(
            "failed to mark business message %s as read in chat %s", message_id, chat_id, exc_info=True
        )


async def telegram_photo_to_data_url(bot: Bot, file_id: str) -> str:
    """Скачивает фото из Telegram по file_id и возвращает data URL для передачи в OpenAI.

    Фото не отдаётся внешнему сервису ссылкой вида api.telegram.org/file/bot<TOKEN>/..., чтобы не утекал токен бота.
    Telegram отдаёт `message.photo` всегда в JPEG.
    """
    buffer = io.BytesIO()
    await bot.download(file_id, destination=buffer)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def escape_markdown_v2(text: str) -> str:
    return re.sub(r"([_\[\]()~#+>\-=|{}.!])", r"\\\1", text)
