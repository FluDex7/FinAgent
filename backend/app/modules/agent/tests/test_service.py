import pytest
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.modules.agent import service as service_module
from app.modules.agent.service import AgentService, ChatNotFoundError
from app.modules.agent.tests.fakes import FakeToolCallingChatModel


@pytest.fixture
async def session():
    test_engine = create_async_engine(get_settings().database_url)
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        maker = async_sessionmaker(bind=conn, expire_on_commit=False)
        session = maker()
        yield session
        await session.close()
        await trans.rollback()
    await test_engine.dispose()


@pytest.fixture
def agent_service(session) -> AgentService:
    return AgentService(session, Settings())


def _use_fake_model(monkeypatch, responses: list[AIMessage]) -> None:
    fake = FakeToolCallingChatModel(responses=responses)
    monkeypatch.setattr(service_module, "get_chat_model", lambda settings: fake)


async def test_stream_chat_creates_chat_and_persists_reply(monkeypatch, agent_service):
    _use_fake_model(monkeypatch, [AIMessage(content="Привет! Чем помочь?")])

    events = [e async for e in agent_service.stream_chat(None, "Привет", [])]

    kinds = [e["event"] for e in events]
    assert kinds[0] == "chat"
    assert kinds[-1] == "done"
    assert any(e["event"] == "token" for e in events)

    chat_id = events[0]["data"]["chatId"]
    messages = await agent_service.get_messages(chat_id)
    assert [m.role.value for m in messages] == ["user", "agent"]
    assert messages[1].text.strip() == "Привет! Чем помочь?"


async def test_stream_chat_runs_tool_and_emits_block(monkeypatch, agent_service):
    tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "plot_chart",
                "args": {"kind": "bars", "data": [{"label": "Март", "value": 100}]},
                "id": "call1",
            }
        ],
    )
    final = AIMessage(content="Вот график трат.")
    _use_fake_model(monkeypatch, [tool_call, final])

    from app.modules.tools.plot_chart import plot_chart as real_plot_chart

    monkeypatch.setattr(
        "app.modules.agent.registry.build_tools",
        lambda transactions_service, chat_model: [real_plot_chart],
    )

    events = [e async for e in agent_service.stream_chat(None, "покажи график", [])]

    kinds = [e["event"] for e in events]
    assert "tool_start" in kinds
    assert "tool_end" in kinds
    assert "block" in kinds

    block_event = next(e for e in events if e["event"] == "block")
    assert block_event["data"]["kind"] == "bars"

    chat_id = events[0]["data"]["chatId"]
    messages = await agent_service.get_messages(chat_id)
    agent_message = messages[-1]
    assert agent_message.tools is not None
    assert agent_message.tools[0].name == "plot_chart"
    assert agent_message.blocks is not None


async def test_stream_chat_continues_existing_chat_with_history(monkeypatch, agent_service):
    _use_fake_model(monkeypatch, [AIMessage(content="первый ответ")])
    first_events = [e async for e in agent_service.stream_chat(None, "вопрос 1", [])]
    chat_id = first_events[0]["data"]["chatId"]

    _use_fake_model(monkeypatch, [AIMessage(content="второй ответ")])
    import uuid

    second_events = [
        e async for e in agent_service.stream_chat(uuid.UUID(chat_id), "вопрос 2", [])
    ]
    assert second_events[0]["data"]["chatId"] == chat_id

    messages = await agent_service.get_messages(chat_id)
    assert len(messages) == 4


async def test_chats_crud(agent_service):
    created = await agent_service.create_chat("Мой чат")
    assert created.title == "Мой чат"

    chats = await agent_service.list_chats()
    assert any(c.id == created.id for c in chats)

    renamed = await agent_service.rename_chat(created.id, "Новое имя")
    assert renamed.title == "Новое имя"

    await agent_service.delete_chat(created.id)
    with pytest.raises(ChatNotFoundError):
        await agent_service.get_messages(created.id)


async def test_rename_unknown_chat_raises(agent_service):
    import uuid

    with pytest.raises(ChatNotFoundError):
        await agent_service.rename_chat(uuid.uuid4(), "x")
