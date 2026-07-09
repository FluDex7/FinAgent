from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from app.modules.agent.graph import build_agent_graph, parse_critic_verdict
from app.modules.agent.tests.fakes import FakeToolCallingChatModel


@tool
def echo(text: str) -> str:
    """Echoes text back."""
    return f"echo:{text}"


@tool
def boom() -> str:
    """Always raises."""
    raise RuntimeError("kaboom")


async def test_graph_answers_directly_without_tools():
    model = FakeToolCallingChatModel(responses=[AIMessage(content="Привет!")])
    graph = build_agent_graph(model, [])

    result = await graph.ainvoke({"messages": [HumanMessage(content="hi")]})

    assert result["messages"][-1].content == "Привет!"


async def test_graph_runs_full_model_tool_model_loop():
    tool_call = AIMessage(
        content="", tool_calls=[{"name": "echo", "args": {"text": "hi"}, "id": "call1"}]
    )
    final = AIMessage(content="done")
    model = FakeToolCallingChatModel(responses=[tool_call, final])
    graph = build_agent_graph(model, [echo])

    result = await graph.ainvoke({"messages": [HumanMessage(content="hi")]})

    messages = result["messages"]
    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1
    assert tool_messages[0].content == "echo:hi"
    assert messages[-1].content == "done"


async def test_graph_feeds_tool_error_back_instead_of_crashing():
    tool_call = AIMessage(
        content="", tool_calls=[{"name": "boom", "args": {}, "id": "call1"}]
    )
    final = AIMessage(content="Извини, что-то пошло не так.")
    model = FakeToolCallingChatModel(responses=[tool_call, final])
    graph = build_agent_graph(model, [boom])

    result = await graph.ainvoke({"messages": [HumanMessage(content="hi")]})

    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert "kaboom" in tool_messages[0].content
    assert result["messages"][-1].content == "Извини, что-то пошло не так."


async def test_graph_stops_when_model_calls_no_tools():
    model = FakeToolCallingChatModel(responses=[AIMessage(content="ответ без инструментов")])
    graph = build_agent_graph(model, [echo])

    result = await graph.ainvoke({"messages": [HumanMessage(content="hi")]})

    assert len(result["messages"]) == 2


class _RecordingChatModel(FakeToolCallingChatModel):
    """Captures the exact message list handed to every generation call."""

    seen: list[list] = []

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        type(self).seen.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


async def test_graph_reinjects_reminder_as_last_message_on_every_call():
    # The reminder (e.g. the answer-language directive) must come AFTER tool
    # output on every model call — that's the whole point: a directive at the
    # top of the system prompt loses to a screenful of tool data on recency.
    _RecordingChatModel.seen = []
    tool_call = AIMessage(
        content="", tool_calls=[{"name": "echo", "args": {"text": "hi"}, "id": "call1"}]
    )
    final = AIMessage(content="done")
    model = _RecordingChatModel(responses=[tool_call, final])
    graph = build_agent_graph(model, [echo], reminder="Reply in English.")

    result = await graph.ainvoke({"messages": [HumanMessage(content="hi")]})
    assert result["messages"][-1].content == "done"

    assert len(_RecordingChatModel.seen) == 2
    for call_messages in _RecordingChatModel.seen:
        assert call_messages[-1].content == "Reply in English."
    # ...and it must not leak into the persisted graph state.
    assert all(m.content != "Reply in English." for m in result["messages"])


async def test_critic_approval_ends_the_graph():
    answer = AIMessage(content="Вот разбор трат за июнь: продукты — 42 000.")
    verdict = AIMessage(content='{"ok": true}')
    model = FakeToolCallingChatModel(responses=[answer, verdict])
    graph = build_agent_graph(model, [echo], self_check=True)

    result = await graph.ainvoke({"messages": [HumanMessage(content="на что я трачу?")]})

    assert result["messages"][-1].content == answer.content
    assert model.responses == []  # both canned responses consumed: answer + verdict


async def test_critic_rejection_triggers_exactly_one_revision():
    draft = AIMessage(content="You spend the most on Transfers.")
    verdict = AIMessage(content='{"ok": false, "fix": "покажи разбивку по категориям с графиком"}')
    revised = AIMessage(content="Вот полная разбивка по категориям.")
    model = FakeToolCallingChatModel(responses=[draft, verdict, revised])
    graph = build_agent_graph(model, [echo], self_check=True)

    result = await graph.ainvoke({"messages": [HumanMessage(content="на что я трачу?")]})

    # The revision is final — the critic gets one shot, no second review loop.
    assert result["messages"][-1].content == revised.content
    assert model.responses == []
    assert result["critique_rounds"] == 1


async def test_critic_disabled_makes_no_extra_model_calls():
    answer = AIMessage(content="ответ")
    model = FakeToolCallingChatModel(responses=[answer])
    graph = build_agent_graph(model, [echo], self_check=False)

    result = await graph.ainvoke({"messages": [HumanMessage(content="hi")]})

    assert result["messages"][-1].content == "ответ"
    assert model.responses == []


def test_parse_critic_verdict_edge_cases():
    assert parse_critic_verdict('{"ok": true}') == (True, "")
    assert parse_critic_verdict('```json\n{"ok": false, "fix": "add chart"}\n```') == (
        False,
        "add chart",
    )
    # A broken critic must fail open, never block a fine answer.
    assert parse_critic_verdict("не могу решить")[0] is True
    assert parse_critic_verdict('{"ok": false}')[0] is True  # rejection without a fix is noise
    assert parse_critic_verdict("[1, 2]")[0] is True
