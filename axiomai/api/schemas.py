import datetime

from pydantic import BaseModel


class ArticleResponse(BaseModel):
    id: int
    nm_id: int
    title: str | None
    brand_name: str
    image_url: str
    instruction_text: str
    in_stock: bool
    cashback_percent: int

    model_config = {"from_attributes": True}


class CreateBuyerRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    fullname: str
    article_id: int


class BuyerResponse(BaseModel):
    id: int
    cabinet_id: int
    telegram_id: int
    username: str | None
    fullname: str
    nm_id: int
    is_ordered: bool
    is_left_feedback: bool
    is_cut_labels: bool
    is_canceled: bool
    phone_number: str | None
    bank: str | None
    amount: int | None
    is_superbanking_paid: bool
    is_paid_manually: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class CreatePaymentRequest(BaseModel):
    phone_number: str
    bank: str
    amount: int | None = None


class BankResponse(BaseModel):
    name_rus: str
