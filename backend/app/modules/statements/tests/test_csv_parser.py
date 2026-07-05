from decimal import Decimal

import pytest

from app.core.exceptions import StatementParseError
from app.modules.statements.parsers.csv_parser import parse_csv

EN_CSV = (
    b"date,amount,description\n"
    b"2025-01-14,-540.00,PYATEROCHKA 5443\n"
    b"2025-01-15,-1200.50,YANDEX.TAXI\n"
)

RU_CSV = (
    "Дата операции;Сумма операции;Назначение платежа\n"
    "14.01.2025;-540,00;ПЯТЁРОЧКА 5443\n"
    "15.01.2025;-1 200,50;ООО ВКУСВИЛЛ\n"
).encode("utf-8-sig")


def test_parse_csv_en_headers():
    transactions = parse_csv(EN_CSV)
    assert len(transactions) == 2
    assert transactions[0].amount == Decimal("-540.00")
    assert transactions[0].raw_description == "PYATEROCHKA 5443"
    assert transactions[1].date.isoformat() == "2025-01-15"


def test_parse_csv_ru_headers_semicolon_and_thousands_separator():
    transactions = parse_csv(RU_CSV)
    assert len(transactions) == 2
    assert transactions[0].date.isoformat() == "2025-01-14"
    assert transactions[1].amount == Decimal("-1200.50")
    assert transactions[1].raw_description == "ООО ВКУСВИЛЛ"


def test_parse_csv_missing_column_raises_with_hint():
    bad_csv = b"date,amount\n2025-01-14,-540.00\n"
    with pytest.raises(StatementParseError) as exc_info:
        parse_csv(bad_csv)
    assert "описание" in str(exc_info.value)
    assert exc_info.value.hint


def test_parse_csv_bad_date_raises():
    bad_csv = b"date,amount,description\nnot-a-date,-540.00,X\n"
    with pytest.raises(StatementParseError):
        parse_csv(bad_csv)


def test_parse_csv_bad_amount_raises():
    bad_csv = b"date,amount,description\n2025-01-14,abc,X\n"
    with pytest.raises(StatementParseError):
        parse_csv(bad_csv)


def test_parse_csv_no_rows_raises():
    bad_csv = b"date,amount,description\n"
    with pytest.raises(StatementParseError):
        parse_csv(bad_csv)


def test_parse_csv_skips_blank_lines():
    csv_with_blank = (
        b"date,amount,description\n"
        b"2025-01-14,-540.00,PYATEROCHKA 5443\n"
        b"\n"
        b"2025-01-15,-1200.50,YANDEX.TAXI\n"
    )
    transactions = parse_csv(csv_with_blank)
    assert len(transactions) == 2
