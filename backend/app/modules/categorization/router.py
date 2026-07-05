import uuid

from fastapi import APIRouter

from app.modules.categorization.dependencies import TransactionsServiceDep
from app.modules.categorization.schemas import CategoryCreate, CategoryUpdate, MerchantRecategorize
from app.modules.transactions.schemas import CategoryOut, MerchantOut

router = APIRouter(tags=["categorization"])


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(service: TransactionsServiceDep) -> list[CategoryOut]:
    return await service.list_categories()


@router.post("/categories", response_model=CategoryOut)
async def create_category(body: CategoryCreate, service: TransactionsServiceDep) -> CategoryOut:
    return await service.get_or_create_category(body.name, body.color)


@router.patch("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: uuid.UUID, body: CategoryUpdate, service: TransactionsServiceDep
) -> CategoryOut:
    return await service.update_category(category_id, name=body.name, color=body.color)


@router.get("/categories/merchants", response_model=list[MerchantOut])
async def list_merchants(
    service: TransactionsServiceDep, needs_review: bool = False
) -> list[MerchantOut]:
    return await service.list_merchants(needs_review=needs_review)


@router.patch("/categories/merchants/{merchant_id}", response_model=MerchantOut)
async def recategorize_merchant(
    merchant_id: uuid.UUID, body: MerchantRecategorize, service: TransactionsServiceDep
) -> MerchantOut:
    return await service.recategorize_merchant(merchant_id, body.category_id)
