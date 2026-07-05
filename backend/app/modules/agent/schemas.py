import uuid
from datetime import datetime
from typing import Literal

from app.core.schemas import CamelModel
from app.modules.agent.models import MessageRole


class Ref(CamelModel):
    path: str
    kind: Literal["file", "folder"]


class ChatRequest(CamelModel):
    chat_id: uuid.UUID | None = None
    message: str
    refs: list[Ref] = []


class ChatSummary(CamelModel):
    id: uuid.UUID
    title: str


class ChatRename(CamelModel):
    title: str


class ToolCallOut(CamelModel):
    id: str
    name: str
    status: Literal["running", "done", "error"]
    detail: str | None = None


class BlockOut(CamelModel):
    kind: Literal["metrics", "donut", "bars", "line", "table"]
    data: dict | list


class MessageOut(CamelModel):
    id: uuid.UUID
    role: MessageRole
    text: str
    refs: list[Ref] | None = None
    scope: dict | None = None
    tools: list[ToolCallOut] | None = None
    blocks: list[BlockOut] | None = None
    suggestions: list[str] | None = None
    created_at: datetime
