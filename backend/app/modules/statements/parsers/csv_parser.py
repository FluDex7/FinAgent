import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.core.exceptions import StatementParseError
from app.modules.transactions.schemas import TransactionIn

CSV_EXAMPLE = (
    "date,amount,description\n"
    "2025-01-14,-540.00,PYATEROCHKA 5443\n"
    "2025-01-15,-1200.50,YANDEX.TAXI"
)

_DATE_ALIASES = {"date", "дата", "дата операции"}
_AMOUNT_ALIASES = {"amount", "сумма", "сумма операции", "сумма в валюте счета"}
_DESCRIPTION_ALIASES = {
    "description",
    "описание",
    "назначение платежа",
    "merchant",
    "продавец",
    "описание операции",
}

_DATE_FORMATS = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y")


def _resolve_columns(fieldnames: list[str]) -> dict[str, str]:
    normalized = {name.strip().lower(): name for name in fieldnames}

    def find(aliases: set[str], field: str) -> str:
        for alias in aliases:
            if alias in normalized:
                return normalized[alias]
        alias_list = ", ".join(sorted(aliases))
        raise StatementParseError(
            f"В CSV не найдена колонка «{field}» (ожидались варианты: {alias_list}).",
            hint=f"Пример ожидаемого формата:\n{CSV_EXAMPLE}",
        )

    return {
        "date": find(_DATE_ALIASES, "дата"),
        "amount": find(_AMOUNT_ALIASES, "сумма"),
        "description": find(_DESCRIPTION_ALIASES, "описание"),
    }


def _parse_date(raw: str) -> date:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise StatementParseError(
        f"Не удалось разобрать дату «{raw}».",
        hint=f"Пример ожидаемого формата:\n{CSV_EXAMPLE}",
    )


def _parse_amount(raw: str) -> Decimal:
    cleaned = raw.strip().replace("\xa0", "").replace(" ", "").replace("₽", "").replace("RUB", "")
    cleaned = cleaned.replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise StatementParseError(
            f"Не удалось разобрать сумму «{raw}».",
            hint=f"Пример ожидаемого формата:\n{CSV_EXAMPLE}",
        ) from exc


def parse_csv(content: bytes) -> list[TransactionIn]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise StatementParseError(
            "Файл не в кодировке UTF-8.",
            hint=f"Пример ожидаемого формата:\n{CSV_EXAMPLE}",
        ) from exc

    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise StatementParseError(
            "CSV пуст или без заголовка.", hint=f"Пример ожидаемого формата:\n{CSV_EXAMPLE}"
        )

    columns = _resolve_columns(list(reader.fieldnames))

    transactions: list[TransactionIn] = []
    for row in reader:
        if not any(row.values()):
            continue
        transactions.append(
            TransactionIn(
                date=_parse_date(row[columns["date"]]),
                amount=_parse_amount(row[columns["amount"]]),
                raw_description=row[columns["description"]].strip(),
            )
        )

    if not transactions:
        raise StatementParseError(
            "В CSV не найдено ни одной транзакции.",
            hint=f"Пример ожидаемого формата:\n{CSV_EXAMPLE}",
        )

    return transactions
