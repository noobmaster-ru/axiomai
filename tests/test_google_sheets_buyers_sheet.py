"""Юниты на раскладку листа «Покупатели»: строка выгрузки и запросы batchUpdate синка."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from axiomai.infrastructure.google_sheets import (
    BUYERS_SHEET_HEADERS,
    PAID_MANUALLY_COLUMN_INDEX,
    PAID_MANUALLY_COLUMN_LETTER,
    _buyer_to_row,
    _write_buyers_to_sheet,
)


def _make_buyer(**overrides) -> SimpleNamespace:
    fields = dict(
        username="user",
        fullname="User",
        telegram_id=1,
        nm_id=777,
        chat_history=[],
        is_ordered=True,
        is_left_feedback=True,
        is_cut_labels=True,
        phone_number="+79101112233",
        bank="Т-Банк",
        amount=1000,
        cashback_percent=20,
        is_superbanking_paid=False,
        is_paid_manually=False,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_buyer_row_matches_headers_and_contains_percent_and_cashback_amount():
    row = _buyer_to_row(_make_buyer())

    assert len(row) == len(BUYERS_SHEET_HEADERS)
    by_header = dict(zip(BUYERS_SHEET_HEADERS, row))
    assert by_header["Сумма(GPT)"] == "1000"
    assert by_header["Процент кэшбека"] == "20"
    assert by_header["Сумма кэшбека"] == "200"
    assert by_header["Имя в Telegram"] == "user"
    assert by_header["Выплата произведена(superbanking)"] == ""
    assert by_header["Выплатили(руками)"] is False


def test_buyer_row_without_order_price_has_empty_cashback_amount():
    by_header = dict(zip(BUYERS_SHEET_HEADERS, _buyer_to_row(_make_buyer(amount=None))))

    assert by_header["Сумма(GPT)"] == ""
    assert by_header["Процент кэшбека"] == "20"
    assert by_header["Сумма кэшбека"] == ""


def test_buyer_row_with_zero_percent_shows_zero_cashback_not_blank():
    by_header = dict(zip(BUYERS_SHEET_HEADERS, _buyer_to_row(_make_buyer(cashback_percent=0))))

    assert by_header["Сумма кэшбека"] == "0"


def test_paid_manually_checkbox_is_last_column():
    assert PAID_MANUALLY_COLUMN_INDEX == len(BUYERS_SHEET_HEADERS) - 1
    assert PAID_MANUALLY_COLUMN_LETTER == "R"
    assert BUYERS_SHEET_HEADERS[PAID_MANUALLY_COLUMN_INDEX] == "Выплатили(руками)"


async def test_write_buyers_to_sheet_writes_headers_and_moves_checkbox_to_last_column():
    sheets_v4 = MagicMock()
    aiogoogle = MagicMock()
    aiogoogle.as_service_account = AsyncMock(
        side_effect=[
            {
                "sheets": [
                    {
                        "properties": {"title": "Покупатели", "sheetId": 5, "gridProperties": {"rowCount": 1000}},
                        "conditionalFormats": [{}],
                    }
                ]
            },
            None,
        ]
    )

    await _write_buyers_to_sheet(aiogoogle, sheets_v4, "table-1", [_buyer_to_row(_make_buyer())])

    requests = sheets_v4.spreadsheets.batchUpdate.call_args.kwargs["json"]["requests"]
    columns = len(BUYERS_SHEET_HEADERS)

    clear = next(r["updateCells"] for r in requests if "updateCells" in r and "range" in r["updateCells"])
    assert clear["range"]["startRowIndex"] == 1
    assert clear["range"]["endColumnIndex"] == columns

    header = next(r["updateCells"] for r in requests if "updateCells" in r and r["updateCells"].get("start", {}).get("rowIndex") == 0)
    assert [cell["userEnteredValue"]["stringValue"] for cell in header["rows"][0]["values"]] == BUYERS_SHEET_HEADERS

    data = next(r["updateCells"] for r in requests if "updateCells" in r and r["updateCells"].get("start", {}).get("rowIndex") == 1)
    cells = data["rows"][0]["values"]
    assert len(cells) == columns
    assert cells[-1] == {"userEnteredValue": {"boolValue": False}}

    validation = next(r["setDataValidation"] for r in requests if "setDataValidation" in r)
    assert validation["range"]["startColumnIndex"] == columns - 1
    assert validation["range"]["endColumnIndex"] == columns

    highlight = next(r["addConditionalFormatRule"]["rule"] for r in requests if "addConditionalFormatRule" in r)
    assert highlight["ranges"][0]["endColumnIndex"] == columns
    assert highlight["booleanRule"]["condition"]["values"] == [{"userEnteredValue": "=$R2=TRUE"}]
