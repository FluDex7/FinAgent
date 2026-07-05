import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.modules.agent.dependencies import AgentServiceDep
from app.modules.agent.schemas import ChatRename, ChatRequest, ChatSummary, MessageOut

router = APIRouter(tags=["agent"])


def _format_sse(event: dict[str, Any]) -> str:
    payload = json.dumps(event["data"], ensure_ascii=False, default=str)
    return f"event: {event['event']}\ndata: {payload}\n\n"


@router.get("/chats", response_model=list[ChatSummary])
async def list_chats(service: AgentServiceDep) -> list[ChatSummary]:
    return await service.list_chats()


@router.post("/chats", response_model=ChatSummary)
async def create_chat(service: AgentServiceDep) -> ChatSummary:
    return await service.create_chat()


@router.patch("/chats/{chat_id}", response_model=ChatSummary)
async def rename_chat(
    chat_id: uuid.UUID, body: ChatRename, service: AgentServiceDep
) -> ChatSummary:
    return await service.rename_chat(chat_id, body.title)


@router.delete("/chats/{chat_id}", status_code=204)
async def delete_chat(chat_id: uuid.UUID, service: AgentServiceDep) -> None:
    await service.delete_chat(chat_id)


@router.get("/chats/{chat_id}/messages", response_model=list[MessageOut])
async def get_messages(chat_id: uuid.UUID, service: AgentServiceDep) -> list[MessageOut]:
    return await service.get_messages(chat_id)


@router.post("/chat")
async def chat(body: ChatRequest, service: AgentServiceDep) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        async for event in service.stream_chat(body.chat_id, body.message, body.refs):
            yield _format_sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
