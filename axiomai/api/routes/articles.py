from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException

from axiomai.api.schemas import ArticleResponse
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("")
@inject
async def list_articles(
    telegram_id: int,
    cashback_table_gateway: FromDishka[CashbackTableGateway],
) -> list[ArticleResponse]:
    articles = await cashback_table_gateway.get_all_in_stock_articles(telegram_id)
    return [ArticleResponse.model_validate(a) for a in articles]


@router.get("/{article_id}")
@inject
async def get_article(
    article_id: int,
    cashback_table_gateway: FromDishka[CashbackTableGateway],
) -> ArticleResponse:
    article = await cashback_table_gateway.get_cashback_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleResponse.model_validate(article)
