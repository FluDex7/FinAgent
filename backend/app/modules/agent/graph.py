import json
from typing import Annotated, Any, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

from app.modules.agent.prompts import SYSTEM_PROMPT


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def _serialize(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def build_agent_graph(
    chat_model: BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str = SYSTEM_PROMPT,
    reminder: str | None = None,
) -> CompiledStateGraph:
    """The core loop: model -> tools -> model, looping until the model stops calling tools.

    Tool errors are caught here and fed back as a ToolMessage so the model can react
    instead of the whole request blowing up.

    `reminder` is re-injected as the LAST message before every generation. Instructions
    at the top of the system prompt lose to whatever came most recently — e.g. the
    answer-language directive was ignored once a tool returned a screenful of Russian
    transaction data — so recency-sensitive directives go here, not in system_prompt.
    """
    tools_by_name = {t.name: t for t in tools}
    model_with_tools = chat_model.bind_tools(tools) if tools else chat_model

    async def call_model(state: AgentState) -> dict:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_prompt), *messages]
        if reminder:
            messages = [*messages, SystemMessage(content=reminder)]
        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    async def call_tools(state: AgentState) -> dict:
        last = state["messages"][-1]
        assert isinstance(last, AIMessage)  # only routed here when the model requested tools
        tool_messages: list[ToolMessage] = []
        for call in last.tool_calls:
            tool = tools_by_name.get(call["name"])
            if tool is None:
                tool_messages.append(
                    ToolMessage(
                        content=f"Инструмент {call['name']} не найден.",
                        tool_call_id=call["id"],
                        name=call["name"],
                    )
                )
                continue
            try:
                result = await tool.ainvoke(call["args"])
                content = result if isinstance(result, str) else _serialize(result)
            except Exception as exc:  # noqa: BLE001 - a tool failure must not crash the graph
                content = f"Ошибка инструмента: {exc}"
            tool_messages.append(
                ToolMessage(content=content, tool_call_id=call["id"], name=call["name"])
            )
        return {"messages": tool_messages}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", call_tools)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()
