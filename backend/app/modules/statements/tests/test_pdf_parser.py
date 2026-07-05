from decimal import Decimal
from pathlib import Path

import pytest

from app.core.exceptions import StatementParseError
from app.modules.statements.parsers.pdf_parser import parse_pdf

FIXTURES = Path(__file__).parent / "fixtures" / "pdf_samples"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_parses_tbank_statement_and_matches_documents_own_totals():
    transactions = parse_pdf(_load("tbank_funds_movement.pdf"))

    assert len(transactions) == 93
    assert all(t.date.year == 2026 for t in transactions)

    total = sum(t.amount for t in transactions)
    # The PDF's own footer states Пополнения 59 275.20 / Расходы 55 829.29.
    assert total == Decimal("3445.91")

    first = transactions[0]
    assert first.date.isoformat() == "2026-06-30"
    assert first.amount == Decimal("-235.98")
    assert "MAGNIT MM" in first.raw_description
    assert "KUANTRO" in first.raw_description  # wrapped continuation line was appended


def test_parses_sberbank_statement_and_matches_documents_own_totals():
    transactions = parse_pdf(_load("sberbank_account_statement.pdf"))

    assert len(transactions) == 165

    total = sum(t.amount for t in transactions)
    # Остаток на 01.06.2024 16 468.28 -> Остаток на 30.06.2024 30 969.79.
    assert total == Decimal("14501.51")

    first = transactions[0]
    assert first.date.isoformat() == "2024-06-30"
    assert first.amount == Decimal("-38.00")
    assert first.raw_description.startswith("Транспорт:")
    assert "KAZANMETRO" in first.raw_description


def test_sberbank_credit_rows_are_positive_debit_rows_are_negative():
    transactions = parse_pdf(_load("sberbank_account_statement.pdf"))
    credit = next(t for t in transactions if "Перевод от В. Артем" in t.raw_description)
    debit = next(t for t in transactions if "KAZANMETRO" in t.raw_description)

    assert credit.amount > 0
    assert debit.amount < 0


def test_rejects_pdf_with_no_recognizable_format():
    with pytest.raises(StatementParseError):
        parse_pdf(b"%PDF-1.4\n%not a real pdf, and definitely not a bank statement\n")
