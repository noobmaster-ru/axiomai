from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException

from axiomai.api.schemas import BuyerResponse, CreateBuyerRequest, CreatePaymentRequest
from axiomai.application.interactors.create_buyer import CreateBuyer
from axiomai.application.interactors.create_superbanking_payment import CreateSuperbankingPayment
from axiomai.application.interactors.update_buyer_screenshot import ScreenshotType, UpdateBuyerScreenshot
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway

router = APIRouter(prefix="/buyers", tags=["buyers"])


@router.post("", status_code=201)
@inject
async def create_buyer(
    body: CreateBuyerRequest,
    create_buyer_interactor: FromDishka[CreateBuyer],
) -> BuyerResponse:
    buyer = await create_buyer_interactor.execute(
        telegram_id=body.telegram_id,
        username=body.username,
        fullname=body.fullname,
        article_id=body.article_id,
    )
    return BuyerResponse.model_validate(buyer)


@router.get("/{buyer_id}")
@inject
async def get_buyer(
    buyer_id: int,
    buyer_gateway: FromDishka[BuyerGateway],
) -> BuyerResponse:
    buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    return BuyerResponse.model_validate(buyer)


@router.post("/{buyer_id}/screenshots/order")
@inject
async def upload_order_screenshot(
    buyer_id: int,
    update_screenshot: FromDishka[UpdateBuyerScreenshot],
) -> BuyerResponse:
    try:
        buyer = await update_screenshot.execute(buyer_id, ScreenshotType.ORDER)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return BuyerResponse.model_validate(buyer)


@router.post("/{buyer_id}/screenshots/feedback")
@inject
async def upload_feedback_screenshot(
    buyer_id: int,
    update_screenshot: FromDishka[UpdateBuyerScreenshot],
) -> BuyerResponse:
    try:
        buyer = await update_screenshot.execute(buyer_id, ScreenshotType.FEEDBACK)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return BuyerResponse.model_validate(buyer)


@router.post("/{buyer_id}/screenshots/barcode")
@inject
async def upload_cut_labels_screenshot(
    buyer_id: int,
    update_screenshot: FromDishka[UpdateBuyerScreenshot],
) -> BuyerResponse:
    try:
        buyer = await update_screenshot.execute(buyer_id, ScreenshotType.CUT_LABELS)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return BuyerResponse.model_validate(buyer)


@router.post("/{buyer_id}/complete", status_code=201)
@inject
async def create_payment(
    buyer_id: int,
    body: CreatePaymentRequest,
    buyer_gateway: FromDishka[BuyerGateway],
    create_superbanking_payment: FromDishka[CreateSuperbankingPayment],
) -> BuyerResponse:
    buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")

    await create_superbanking_payment.execute(
        telegram_id=buyer.telegram_id,
        cabinet_id=buyer.cabinet_id,
        phone_number=body.phone_number,
        bank=body.bank,
        amount=body.amount,
        send_notifications=False,
    )

    buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
    return BuyerResponse.model_validate(buyer)
