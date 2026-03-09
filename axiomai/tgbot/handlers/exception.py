from aiogram import F, Router
from aiogram.filters import ExceptionTypeFilter
from aiogram.types import ErrorEvent, Message
from dishka.integrations.aiogram import inject

from axiomai.application.exceptions.cabinet import CabinetNotFoundError
from axiomai.application.exceptions.cashback_table import CashbackTableNotFoundError

router = Router()


@router.error(ExceptionTypeFilter(CabinetNotFoundError), F.update.message.as_("message"))
@inject
async def cabinet_not_found_handler(event: ErrorEvent, message: Message) -> None:
    await message.answer("❗ Личный кабинет не найден. Пожалуйста, зарегистрируйтесь. /start")


@router.error(ExceptionTypeFilter(CashbackTableNotFoundError), F.update.message.as_("message"))
@inject
async def cashback_table_not_found_handler(event: ErrorEvent, message: Message) -> None:
    await message.answer("❗ Таблица кэшбека не найдена. Пожалуйста, создайте ее. /start")
