from dataclasses import dataclass


@dataclass
class CashbackArticle:
    nm_id: int
    title: str
    brand_name: str
    instruction_text: str
    image_url: str
    in_stock: bool
    cashback_percent: int
    price: int | None = None  # цена на ВБ в рублях, колонка K таблицы
