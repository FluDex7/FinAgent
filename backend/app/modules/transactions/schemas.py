import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.core.schemas import CamelModel


class TransactionIn(BaseModel):
    date: date
    amount: Decimal
    currency: str = "RUB"
    raw_description: str


class TransactionOut(CamelModel):
    id: uuid.UUID
    date: date
    amount: Decimal
    currency: str
    raw_description: str
    merchant_id: uuid.UUID | None
    category_id: uuid.UUID | None
