import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.transactions.models import Transaction
from app.modules.transactions.schemas import TransactionIn


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(
        self, statement_id: uuid.UUID, transactions: list[TransactionIn]
    ) -> list[Transaction]:
        rows = [
            Transaction(
                statement_id=statement_id,
                date=t.date,
                amount=t.amount,
                currency=t.currency,
                raw_description=t.raw_description,
            )
            for t in transactions
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def list_by_statement(
        self, statement_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .where(Transaction.statement_id == statement_id)
            .order_by(Transaction.date)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def execute_readonly_query(
        self, sql: str, *, timeout_ms: int = 3000
    ) -> list[dict]:
        """Runs an already-validated (SELECT-only, whitelisted) SQL string for sql_query."""
        await self.session.execute(text(f"SET LOCAL statement_timeout = {timeout_ms}"))
        result = await self.session.execute(text(sql))
        return [dict(row._mapping) for row in result.fetchall()]
