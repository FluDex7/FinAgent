import uuid

from app.core.schemas import CamelModel


class CategoryCreate(CamelModel):
    name: str
    color: str = "#94a3b8"


class CategoryUpdate(CamelModel):
    name: str | None = None
    color: str | None = None


class MerchantRecategorize(CamelModel):
    category_id: uuid.UUID
