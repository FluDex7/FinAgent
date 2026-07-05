from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from app.modules.agent.graph import build_agent_graph
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
