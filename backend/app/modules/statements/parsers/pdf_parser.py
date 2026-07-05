import re
import subprocess
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_bytes

from app.core.exceptions import StatementParseError
from app.modules.transactions.schemas import TransactionIn

_DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")
_AUTH_CODE_RE = re.compile(r"^\d{4,}$")
_AMOUNT_TOKEN_RE = re.compile(r"^[+-]?[\d\s\xa0.,]+")

# Repeated per-page headers/footers (bank letterhead, legal boilerplate, page numbers) that
# must never be swallowed into a transaction's wrapped description.
_TBANK_NOISE_MARKERS = (
    "АО «ТБАНК»",
    "БИК ",
    "ПОПОЛНЕНИЯ:",
    "РАСХОДЫ:",
    "С УВАЖЕНИЕМ",
    "РУКОВОДИТЕЛЬ УПРАВЛЕНИЯ",
    "ДВИЖЕНИЕ СРЕДСТВ ЗА ПЕРИОД",
    "ДАТА И ВРЕМЯ",
    "В ВАЛЮТЕ КАРТЫ",
)


def _is_noise_line(line: str, markers: tuple[str, ...]) -> bool:
    stripped = line.strip()
    if not stripped or stripped.isdigit():
        return True
    upper = stripped.upper()
    return any(marker in upper for marker in markers)

_MIN_NATIVE_TEXT_LENGTH = 200
"""Below this, a PDF has effectively no embedded text — it's a scan, OCR is needed."""


def _extract_native_text(content: bytes) -> str:
    """pdftotext -layout preserves column alignment for digitally-generated
    statements (the overwhelmingly common case) far better than OCR ever could,
    since it reads real glyph positions instead of re-recognizing pixels."""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-", "-"],
            input=content,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8", errors="ignore")


def _preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )


def _extract_ocr_text(content: bytes) -> str:
    """Fallback for genuinely scanned/photographed statements with no embedded text."""
    try:
        pages = convert_from_bytes(content, dpi=300)
    except Exception:  # noqa: BLE001 - not a valid/renderable PDF; let parse_pdf report it
        return ""
    texts = []
    for page in pages:
        preprocessed = _preprocess_for_ocr(np.array(page))
        texts.append(pytesseract.image_to_string(preprocessed, lang="rus+eng"))
    return "\n".join(texts)


def _split_columns(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"\s{2,}", line.strip()) if c.strip()]


def _parse_date(raw: str) -> date:
    return datetime.strptime(raw, "%d.%m.%Y").date()


def _clean_amount(raw: str) -> Decimal:
    cleaned = raw.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise StatementParseError(f"Не удалось разобрать сумму «{raw}» в PDF.") from exc


def _parse_tbank_text(text: str) -> list[TransactionIn]:
    transactions: list[TransactionIn] = []
    current: dict[str, str] | None = None

    for raw_line in text.splitlines():
        if _is_noise_line(raw_line, _TBANK_NOISE_MARKERS):
            continue
        columns = _split_columns(raw_line)
        if not columns:
            continue

        if len(columns) >= 5 and _DATE_RE.match(columns[0]) and _DATE_RE.match(columns[1]):
            if current is not None:
                transactions.append(_finalize_tbank_row(current))
            current = {"date": columns[0], "amount": columns[2], "description": columns[4]}
        elif current is not None and _TIME_RE.match(columns[0]):
            if len(columns) >= 3:
                current["description"] += " " + columns[-1]
        elif current is not None:
            current["description"] += " " + " ".join(columns)

    if current is not None:
        transactions.append(_finalize_tbank_row(current))

    return transactions


def _finalize_tbank_row(row: dict[str, str]) -> TransactionIn:
    # row["amount"] is like "-6 000.00 ₽" — extract the numeric run (keeping the
    # thousands-separator space) and drop the trailing currency symbol.
    match = _AMOUNT_TOKEN_RE.match(row["amount"])
    amount_token = match.group(0) if match else row["amount"]
    return TransactionIn(
        date=_parse_date(row["date"]),
        amount=_clean_amount(amount_token),
        raw_description=re.sub(r"\s+", " ", row["description"]).strip(),
    )


def _parse_sberbank_text(text: str) -> list[TransactionIn]:
    transactions: list[TransactionIn] = []
    pending: dict[str, str] | None = None

    for raw_line in text.splitlines():
        columns = _split_columns(raw_line)
        if len(columns) < 2:
            continue

        if len(columns) >= 4 and _DATE_RE.match(columns[0]) and _TIME_RE.match(columns[1]):
            pending = {"date": columns[0], "category": columns[2], "amount": columns[3]}
        elif (
            pending is not None
            and _DATE_RE.match(columns[0])
            and _AUTH_CODE_RE.match(columns[1])
        ):
            description = columns[2] if len(columns) >= 3 else ""
            transactions.append(_finalize_sber_row(pending, description))
            pending = None

    return transactions


def _finalize_sber_row(pending: dict[str, str], description: str) -> TransactionIn:
    amount_str = pending["amount"]
    is_credit = amount_str.startswith("+")
    value = _clean_amount(amount_str.lstrip("+"))
    if not is_credit:
        value = -value
    combined = f"{pending['category']}: {description}".strip(": ").strip()
    return TransactionIn(
        date=_parse_date(pending["date"]),
        amount=value,
        raw_description=re.sub(r"\s+", " ", combined).strip(),
    )


def _detect_format(text: str) -> str:
    upper = text.upper()
    if "ТБАНК" in upper or "TBANK" in upper or "СПРАВКА О ДВИЖЕНИИ СРЕДСТВ" in upper:
        return "tbank"
    if "СБЕР" in upper or "SBER" in upper or "ВЫПИСКА ПО ПЛАТЁЖНОМУ СЧЁТУ" in upper:
        return "sberbank"
    return "unknown"


def parse_pdf(content: bytes) -> list[TransactionIn]:
    text = _extract_native_text(content)
    if len(text.strip()) < _MIN_NATIVE_TEXT_LENGTH:
        text = _extract_ocr_text(content)

    if not text.strip():
        raise StatementParseError(
            "Не удалось извлечь текст из PDF.",
            hint="Убедитесь, что файл не повреждён и не защищён паролем.",
        )

    fmt = _detect_format(text)
    if fmt == "tbank":
        transactions = _parse_tbank_text(text)
    elif fmt == "sberbank":
        transactions = _parse_sberbank_text(text)
    else:
        raise StatementParseError(
            "Формат PDF-выписки не распознан.",
            hint="Пока поддерживаются выписки Т-Банка и Сбербанка.",
        )

    if not transactions:
        raise StatementParseError("В PDF не найдено ни одной транзакции.")

    return transactions
