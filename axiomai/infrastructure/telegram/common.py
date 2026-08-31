import base64
import io
import re

from aiogram import Bot


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
