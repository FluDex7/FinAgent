from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.transactions.service import TransactionsService


def get_transactions_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TransactionsService:
    return TransactionsService(session)


TransactionsServiceDep = Annotated[TransactionsService, Depends(get_transactions_service)]
