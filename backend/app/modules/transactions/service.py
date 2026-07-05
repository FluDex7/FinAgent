import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.transactions.repository import TransactionRepository
from app.modules.transactions.schemas import TransactionIn, TransactionOut


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
