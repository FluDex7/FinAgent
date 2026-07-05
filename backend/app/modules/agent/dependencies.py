from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.modules.agent.service import AgentService


def get_agent_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentService:
    return AgentService(session, settings)


AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
