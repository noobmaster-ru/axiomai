from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from axiomai.infrastructure.superbanking import Superbanking

router = APIRouter(prefix="/banks", tags=["banks"])


@router.get("")
@inject
async def list_banks(
    superbanking: FromDishka[Superbanking],
) -> list[str]:
    return [b["name_rus"] for b in superbanking.get_banks()]
