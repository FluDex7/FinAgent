import uuid
from decimal import Decimal

from sqlalchemy import ColumnElement, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.transactions.models import Category, Merchant, MerchantSource, Transaction
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

    async def list_categories(self) -> list[Category]:
        result = await self.session.execute(select(Category))
        return list(result.scalars().all())

    async def get_category_by_name(self, name: str) -> Category | None:
        result = await self.session.execute(select(Category).where(Category.name == name))
        return result.scalar_one_or_none()

    async def get_or_create_category(self, name: str, color: str = "#94a3b8") -> Category:
        category = await self.get_category_by_name(name)
        if category is not None:
            return category
        category = Category(name=name, color=color)
        self.session.add(category)
        await self.session.flush()
        return category

    async def get_merchant(self, normalized_key: str) -> Merchant | None:
        stmt = select(Merchant).where(Merchant.normalized_key == normalized_key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_merchant(
        self,
        normalized_key: str,
        category_id: uuid.UUID | None,
        source: MerchantSource,
    ) -> Merchant:
        merchant = await self.get_merchant(normalized_key)
        if merchant is None:
            merchant = Merchant(
                normalized_key=normalized_key, category_id=category_id, source=source
            )
            self.session.add(merchant)
        else:
            merchant.category_id = category_id
            merchant.source = source
        await self.session.flush()
        return merchant

    async def update_transaction_category(
        self,
        transaction_id: uuid.UUID,
        merchant_id: uuid.UUID | None,
        category_id: uuid.UUID | None,
    ) -> None:
        transaction = await self.session.get(Transaction, transaction_id)
        if transaction is None:
            return
        transaction.merchant_id = merchant_id
        transaction.category_id = category_id
        await self.session.flush()

    async def sum_by_category(
        self, statement_ids: list[uuid.UUID], *, expenses_only: bool = False
    ) -> dict[uuid.UUID | None, Decimal]:
        conditions: list[ColumnElement[bool]] = [Transaction.statement_id.in_(statement_ids)]
        if expenses_only:
            conditions.append(Transaction.amount < 0)
        stmt = (
            select(Transaction.category_id, func.sum(Transaction.amount))
            .where(*conditions)
            .group_by(Transaction.category_id)
        )
        result = await self.session.execute(stmt)
        return dict(result.all())

    async def list_merchants(self, *, needs_review: bool = False) -> list[Merchant]:
        stmt = select(Merchant).order_by(Merchant.normalized_key)
        if needs_review:
            stmt = stmt.where(Merchant.source == MerchantSource.llm)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_merchant_by_id(self, merchant_id: uuid.UUID) -> Merchant | None:
        return await self.session.get(Merchant, merchant_id)

    async def recategorize_merchant(
        self, merchant: Merchant, category_id: uuid.UUID
    ) -> None:
        merchant.category_id = category_id
        merchant.source = MerchantSource.user
        await self.session.execute(
            update(Transaction)
            .where(Transaction.merchant_id == merchant.id)
            .values(category_id=category_id)
        )
        await self.session.flush()

    async def update_category(
        self, category: Category, *, name: str | None, color: str | None
    ) -> None:
        if name is not None:
            category.name = name
        if color is not None:
            category.color = color
        await self.session.flush()

    async def get_category(self, category_id: uuid.UUID) -> Category | None:
        return await self.session.get(Category, category_id)
