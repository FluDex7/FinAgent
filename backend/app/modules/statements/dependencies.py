from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.modules.statements.service import StatementsService


def get_statements_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StatementsService:
    return StatementsService(session, settings)


StatementsServiceDep = Annotated[StatementsService, Depends(get_statements_service)]
