import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent.models import Chat, ChatMessage, MessageRole


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, title: str = "Новый чат") -> Chat:
        chat = Chat(title=title)
        self.session.add(chat)
        await self.session.flush()
        return chat

    async def get(self, chat_id: uuid.UUID) -> Chat | None:
        return await self.session.get(Chat, chat_id)

    async def list_all(self) -> list[Chat]:
        stmt = select(Chat).order_by(Chat.updated_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def rename(self, chat: Chat, title: str) -> None:
        chat.title = title
        await self.session.flush()

    async def delete(self, chat: Chat) -> None:
        await self.session.delete(chat)
        await self.session.flush()

    async def touch(self, chat: Chat) -> None:
        await self.session.flush()
        await self.session.refresh(chat)

    async def add_message(
        self,
        chat_id: uuid.UUID,
        role: MessageRole,
        text: str,
        *,
        refs: list[dict] | None = None,
        scope: dict | None = None,
        tools: list[dict] | None = None,
        blocks: list[dict] | None = None,
        suggestions: list[str] | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            chat_id=chat_id,
            role=role,
            text=text,
            refs=refs,
            scope=scope,
            tools=tools,
            blocks=blocks,
            suggestions=suggestions,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_messages(self, chat_id: uuid.UUID) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
            .order_by(ChatMessage.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
