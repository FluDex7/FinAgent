import uuid
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.agent.graph import build_agent_graph
from app.modules.agent.models import Chat, MessageRole
from app.modules.agent.prompts import SYSTEM_PROMPT
from app.modules.agent.registry import build_tools
from app.modules.agent.repository import ChatRepository
from app.modules.agent.schemas import ChatSummary, MessageOut, Ref
from app.modules.statements.service import StatementsService
from app.modules.tools.resolve_scope import resolve_scope
from app.modules.transactions.service import TransactionsService
from app.shared.llm import get_chat_model


class ChatNotFoundError(AppError):
    status_code = 404


def _title_from_message(message: str) -> str:
    trimmed = message.strip()
    if not trimmed:
        return "Новый чат"
    return trimmed[:40] + "…" if len(trimmed) > 40 else trimmed


def _tool_detail(name: str, output: Any) -> str | None:
    if not isinstance(output, dict):
        return None
    if name == "sql_query":
        return output.get("sql")
    if name == "plot_chart":
        return f"{output.get('kind')}: {len(output.get('data') or [])} точек"
    return None


class AgentService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.repo = ChatRepository(session)
        self.transactions = TransactionsService(session)
        self.statements = StatementsService(session, settings)
        self.settings = settings

    async def list_chats(self) -> list[ChatSummary]:
        chats = await self.repo.list_all()
        return [ChatSummary(id=c.id, title=c.title) for c in chats]

    async def create_chat(self, title: str = "Новый чат") -> ChatSummary:
        chat = await self.repo.create(title)
        return ChatSummary(id=chat.id, title=chat.title)

    async def rename_chat(self, chat_id: uuid.UUID, title: str) -> ChatSummary:
        chat = await self._get_or_404(chat_id)
        await self.repo.rename(chat, title)
        return ChatSummary(id=chat.id, title=chat.title)

    async def delete_chat(self, chat_id: uuid.UUID) -> None:
        chat = await self._get_or_404(chat_id)
        await self.repo.delete(chat)

    async def get_messages(self, chat_id: uuid.UUID) -> list[MessageOut]:
        await self._get_or_404(chat_id)
        rows = await self.repo.list_messages(chat_id)
        return [MessageOut.model_validate(r) for r in rows]

    async def _get_or_404(self, chat_id: uuid.UUID) -> Chat:
        chat = await self.repo.get(chat_id)
        if chat is None:
            raise ChatNotFoundError(f"Чат {chat_id} не найден.")
        return chat

    async def stream_chat(
        self, chat_id: uuid.UUID | None, message: str, refs: list[Ref]
    ) -> AsyncIterator[dict[str, Any]]:
        """Runs the LangGraph loop and yields SSE-shaped events as it goes.

        Event order is: chat -> tool_start/tool_end (+ block) per tool call,
        interleaved with token deltas -> done. A failure anywhere yields error
        instead of raising, so the HTTP layer can close the stream cleanly.
        """
        if chat_id is None:
            chat = await self.repo.create(_title_from_message(message))
        else:
            chat = await self._get_or_404(chat_id)

        yield {"event": "chat", "data": {"chatId": str(chat.id)}}

        history_rows = await self.repo.list_messages(chat.id)
        history: list[HumanMessage | AIMessage] = [
            HumanMessage(content=row.text)
            if row.role == MessageRole.user
            else AIMessage(content=row.text)
            for row in history_rows
        ]

        await self.repo.add_message(
            chat.id,
            MessageRole.user,
            message,
            refs=[r.model_dump() for r in refs] or None,
        )

        scope_files: list[str] = []
        scope_auto = False
        tool_calls: list[dict[str, Any]] = []
        blocks: list[dict[str, Any]] = []
        final_text = ""

        try:
            # get_chat_model can raise immediately (e.g. missing OPENAI_API_KEY), and so can
            # resolve_scope's own LLM call — both must surface as `error`, not crash the stream.
            chat_model = get_chat_model(self.settings)
            statement_ids: list[str] = []

            if refs:
                scope_files = [r.path for r in refs]
                statement_ids = await self.statements.resolve_paths_to_statement_ids(scope_files)
                yield {"event": "scope", "data": {"files": scope_files, "auto": False}}
            else:
                tree = await self.statements.browse_tree()
                if any(folder.files for folder in tree):
                    resolution = await resolve_scope(chat_model, message, tree)
                    if resolution.needs_clarification:
                        clarification = resolution.clarification or ""
                        await self.repo.add_message(chat.id, MessageRole.agent, clarification)
                        yield {"event": "token", "data": {"text": clarification}}
                        yield {"event": "done", "data": {}}
                        return
                    scope_auto = True
                    scope_files = resolution.files
                    statement_ids = await self.statements.resolve_paths_to_statement_ids(
                        scope_files
                    )
                    yield {"event": "scope", "data": {"files": scope_files, "auto": True}}

            system_prompt = SYSTEM_PROMPT
            if statement_ids:
                ids_note = ", ".join(statement_ids)
                system_prompt = (
                    f"{SYSTEM_PROMPT}\n\nОбласть данных этого вопроса уже определена и ограничена "
                    f"statement_ids: {ids_note}. Данные уже доступны — сразу вызывай sql_query с "
                    "этими statement_ids. Не спрашивай период и не проси прикрепить/загрузить файл."
                )

            tools = build_tools(self.transactions, self.statements, chat_model, self.settings)
            graph = build_agent_graph(chat_model, tools, system_prompt=system_prompt)

            inputs = {"messages": [*history, HumanMessage(content=message)]}
            async for event in graph.astream_events(inputs, version="v2"):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        yield {"event": "token", "data": {"text": chunk.content}}

                elif kind == "on_chat_model_end":
                    output = event["data"]["output"]
                    if not getattr(output, "tool_calls", None):
                        final_text = output.content

                elif kind == "on_tool_start":
                    call_id = str(event["run_id"])
                    tool_calls.append({"id": call_id, "name": event["name"], "status": "running"})
                    yield {"event": "tool_start", "data": {"id": call_id, "name": event["name"]}}

                elif kind == "on_tool_end":
                    call_id = str(event["run_id"])
                    output = event["data"].get("output")
                    detail = _tool_detail(event["name"], output)
                    for call in tool_calls:
                        if call["id"] == call_id:
                            call["status"] = "done"
                            call["detail"] = detail
                    yield {
                        "event": "tool_end",
                        "data": {"id": call_id, "name": event["name"], "detail": detail},
                    }
                    if event["name"] == "plot_chart" and isinstance(output, dict):
                        blocks.append(output)
                        yield {"event": "block", "data": output}
        except Exception as exc:  # noqa: BLE001 - surfaced to the client, not a crash
            yield {"event": "error", "data": {"message": str(exc)}}
            return

        await self.repo.add_message(
            chat.id,
            MessageRole.agent,
            final_text,
            scope={"files": scope_files, "auto": scope_auto} if scope_files else None,
            tools=tool_calls or None,
            blocks=blocks or None,
        )
        yield {"event": "done", "data": {}}
