import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.core.schemas import CamelModel
from app.modules.transactions.models import MerchantSource


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


class CategoryOut(CamelModel):
    id: uuid.UUID
    name: str
    color: str
    is_system: bool


class MerchantOut(CamelModel):
    id: uuid.UUID
    normalized_key: str
    display_name: str | None
    category_id: uuid.UUID | None
    source: MerchantSource
