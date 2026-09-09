import logging

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject
from dishka import AsyncContainer

from axiomai.config import Config

logger = logging.getLogger(__name__)


class IsAdminFilter(BaseFilter):
    """Пропускает событие только от пользователя из Config.admin_telegram_ids."""

    async def __call__(self, event: TelegramObject, dishka_container: AsyncContainer) -> bool:
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        config = await dishka_container.get(Config)
        if user.id not in config.admin_telegram_ids:
            logger.warning("non-admin user %s tried to use admin action", user.id)
            return False
        return True
