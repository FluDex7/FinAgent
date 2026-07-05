import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.statements.models import Statement, StatementFormat, StatementStatus


class StatementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_path(self, folder_path: str, filename: str) -> Statement | None:
        stmt = select(Statement).where(
            Statement.folder_path == folder_path, Statement.filename == filename
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get(self, statement_id: uuid.UUID) -> Statement | None:
        return await self.session.get(Statement, statement_id)

    async def list_all(self) -> list[Statement]:
        result = await self.session.execute(select(Statement))
        return list(result.scalars().all())

    async def create(
        self, filename: str, folder_path: str, source_format: StatementFormat
    ) -> Statement:
        row = Statement(filename=filename, folder_path=folder_path, source_format=source_format)
        self.session.add(row)
        await self.session.flush()
        return row

    async def mark_parsed(
        self,
        statement: Statement,
        *,
        transaction_count: int,
        date_from: date | None,
        date_to: date | None,
    ) -> None:
        statement.status = StatementStatus.parsed
        statement.transaction_count = transaction_count
        statement.date_from = date_from
        statement.date_to = date_to
        statement.error_message = None
        await self.session.flush()

    async def mark_error(self, statement: Statement, message: str) -> None:
        statement.status = StatementStatus.error
        statement.error_message = message
        await self.session.flush()

    async def delete(self, statement: Statement) -> None:
        await self.session.delete(statement)
        await self.session.flush()

    async def rename(self, statement: Statement, filename: str) -> None:
        statement.filename = filename
        await self.session.flush()
