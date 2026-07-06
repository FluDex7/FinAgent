import pytest
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.modules.agent import service as service_module
from app.modules.agent.schemas import Ref
from app.modules.agent.service import AgentService, ChatNotFoundError
from app.modules.agent.tests.fakes import FakeToolCallingChatModel

CSV_CONTENT = b"date,amount,description\n2025-01-14,-540.00,PYATEROCHKA 5443\n"


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
def agent_service(session, tmp_path) -> AgentService:
    return AgentService(session, Settings(statements_dir=str(tmp_path)))


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
        lambda transactions_service, statements_service, chat_model, settings: [real_plot_chart],
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


async def test_stream_chat_discards_narration_from_a_tool_calling_turn(monkeypatch, agent_service):
    # Some models interleave pre-tool-call narration (or even a leaked SQL query)
    # into the same turn's content alongside a tool call — that text must never
    # reach the user or get persisted, only the later tool-free answer should.
    tool_call = AIMessage(
        content="Сейчас посчитаю. SELECT SUM(amount) FROM transactions;",
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
        lambda transactions_service, statements_service, chat_model, settings: [real_plot_chart],
    )

    events = [e async for e in agent_service.stream_chat(None, "покажи график", [])]

    token_text = "".join(e["data"]["text"] for e in events if e["event"] == "token")
    assert "SELECT" not in token_text
    assert "Сейчас посчитаю" not in token_text
    assert token_text.strip() == "Вот график трат."

    chat_id = events[0]["data"]["chatId"]
    messages = await agent_service.get_messages(chat_id)
    assert "SELECT" not in messages[-1].text


async def test_stream_chat_strips_sql_leaked_into_the_final_tool_free_answer(
    monkeypatch, agent_service
):
    # Some models copy sql_query's own generated SQL verbatim into what IS their
    # genuine final (tool-free) answer, e.g. after seeing it in a ToolMessage —
    # the run_id-buffering discard doesn't help here since this turn has no tool
    # call of its own; a deterministic sanitizer is the only reliable fix.
    final = AIMessage(
        content=(
            "SELECT category_id, SUM(amount) AS total FROM transactions "
            "WHERE statement_id IN ('x') GROUP BY category_id;"
            "Вот основные категории ваших трат."
        )
    )
    _use_fake_model(monkeypatch, [final])

    events = [e async for e in agent_service.stream_chat(None, "на что я трачу", [])]

    token_text = "".join(e["data"]["text"] for e in events if e["event"] == "token")
    assert "SELECT" not in token_text
    assert token_text.strip() == "Вот основные категории ваших трат."

    chat_id = events[0]["data"]["chatId"]
    messages = await agent_service.get_messages(chat_id)
    assert "SELECT" not in messages[-1].text


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


async def test_explicit_refs_emit_scope_and_skip_resolution(monkeypatch, agent_service):
    await agent_service.statements.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)
    _use_fake_model(monkeypatch, [AIMessage(content="Вот ответ по Q1.")])

    refs = [Ref(path="2025/q1", kind="file")]
    events = [e async for e in agent_service.stream_chat(None, "сколько потратил?", refs)]

    kinds = [e["event"] for e in events]
    assert kinds[0] == "chat"
    assert kinds[1] == "scope"
    assert events[1]["data"] == {"files": ["2025/q1"], "auto": False}

    chat_id = events[0]["data"]["chatId"]
    messages = await agent_service.get_messages(chat_id)
    assert messages[-1].scope == {"files": ["2025/q1"], "auto": False}


async def test_auto_resolves_scope_when_no_refs_given(monkeypatch, agent_service):
    await agent_service.statements.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)

    scope_json = AIMessage(content='{"files": ["2025"], "explanation": "весь 2025 год"}')
    final = AIMessage(content="Вот итог за 2025.")
    _use_fake_model(monkeypatch, [scope_json, final])

    events = [e async for e in agent_service.stream_chat(None, "сколько потратил за 25 год?", [])]

    kinds = [e["event"] for e in events]
    assert kinds[0] == "chat"
    assert kinds[1] == "scope"
    assert events[1]["data"] == {"files": ["2025"], "auto": True}


async def test_suppresses_scope_event_when_resolution_is_empty(monkeypatch, agent_service):
    # A short follow-up like "давай" resolves to no files — showing an empty
    # "scope" banner in that case is confusing, so no event should be emitted.
    await agent_service.statements.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)

    scope_json = AIMessage(content='{"files": [], "explanation": ""}')
    final = AIMessage(content="Вот график.")
    _use_fake_model(monkeypatch, [scope_json, final])

    events = [e async for e in agent_service.stream_chat(None, "давай", [])]

    assert "scope" not in [e["event"] for e in events]


async def test_skips_resolve_scope_when_tree_is_empty(monkeypatch, agent_service):
    _use_fake_model(monkeypatch, [AIMessage(content="Пока нет ни одной выписки.")])

    events = [e async for e in agent_service.stream_chat(None, "сколько я потратил?", [])]

    assert "scope" not in [e["event"] for e in events]


async def test_asks_clarification_instead_of_guessing_ambiguous_scope(monkeypatch, agent_service):
    await agent_service.statements.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)

    clarification = AIMessage(content='{"clarification": "За какой год вас интересует апрель?"}')
    _use_fake_model(monkeypatch, [clarification])

    events = [e async for e in agent_service.stream_chat(None, "траты в апреле", [])]

    assert [e["event"] for e in events] == ["chat", "token", "done"]
    assert "апрель" in events[1]["data"]["text"]

    chat_id = events[0]["data"]["chatId"]
    messages = await agent_service.get_messages(chat_id)
    assert messages[-1].scope is None
    assert "апрель" in messages[-1].text


async def test_resolved_statement_ids_are_injected_into_system_prompt(monkeypatch, agent_service):
    statement = await agent_service.statements.upload(
        filename="q1.csv", folder="2025", content=CSV_CONTENT
    )
    scope_json = AIMessage(content='{"files": ["2025"], "explanation": "весь год"}')
    final = AIMessage(content="ответ")
    _use_fake_model(monkeypatch, [scope_json, final])

    captured: dict = {}
    from app.modules.agent.graph import build_agent_graph as real_build_agent_graph

    def spy_build(chat_model, tools, system_prompt=""):
        captured["system_prompt"] = system_prompt
        return real_build_agent_graph(chat_model, tools, system_prompt=system_prompt)

    monkeypatch.setattr(service_module, "build_agent_graph", spy_build)

    events = [e async for e in agent_service.stream_chat(None, "траты за 25 год", [])]
    assert events[-1]["event"] == "done"

    assert str(statement.id) in captured["system_prompt"]
