from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from axiomai.config import Config
from axiomai.infrastructure.telegram.dialogs.states import MyCabinetStates
from axiomai.infrastructure.telegram.text import MY_CABINET_BUTTON_TEXT, SUPPORT_BUTTON_TEXT

router = Router()


@router.message(F.text == MY_CABINET_BUTTON_TEXT)
async def my_cabinet_handler(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(MyCabinetStates.select_option, mode=StartMode.RESET_STACK)


@router.message(F.text == SUPPORT_BUTTON_TEXT)
@router.message(Command("support"))
@inject
async def support_handler(message: Message, config: FromDishka[Config]) -> None:
    await message.answer(f"Напишите {config.admin_username}, поможем с любыми вопросами")
