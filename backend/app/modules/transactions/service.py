import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.transactions.models import MerchantSource
from app.modules.transactions.repository import TransactionRepository
from app.modules.transactions.schemas import CategoryOut, TransactionIn, TransactionOut


class TransactionsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = TransactionRepository(session)

    async def bulk_create(
        self, statement_id: uuid.UUID, transactions: list[TransactionIn]
    ) -> list[TransactionOut]:
        rows = await self.repo.bulk_create(statement_id, transactions)
        return [TransactionOut.model_validate(r) for r in rows]

    async def list_by_statement(
        self, statement_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[TransactionOut]:
        rows = await self.repo.list_by_statement(statement_id, limit, offset)
        return [TransactionOut.model_validate(r) for r in rows]

    async def run_validated_sql(self, sql: str) -> list[dict]:
        """Executes SQL already checked by sql_validation — the sql_query tool's only DB gateway."""
        return await self.repo.execute_readonly_query(sql)

    async def list_categories(self) -> list[CategoryOut]:
        rows = await self.repo.list_categories()
        return [CategoryOut.model_validate(r) for r in rows]

    async def get_or_create_category(self, name: str, color: str = "#94a3b8") -> CategoryOut:
        row = await self.repo.get_or_create_category(name, color)
        return CategoryOut.model_validate(row)

    async def get_merchant(self, normalized_key: str) -> tuple[uuid.UUID, uuid.UUID | None] | None:
        merchant = await self.repo.get_merchant(normalized_key)
        if merchant is None:
            return None
        return merchant.id, merchant.category_id

    async def upsert_merchant(
        self, normalized_key: str, category_id: uuid.UUID | None, source: MerchantSource
    ) -> uuid.UUID:
        merchant = await self.repo.upsert_merchant(normalized_key, category_id, source)
        return merchant.id

    async def set_transaction_category(
        self,
        transaction_id: uuid.UUID,
        merchant_id: uuid.UUID | None,
        category_id: uuid.UUID | None,
    ) -> None:
        await self.repo.update_transaction_category(transaction_id, merchant_id, category_id)
