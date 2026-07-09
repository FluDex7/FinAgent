import json
import re
from collections.abc import Hashable
from typing import Annotated, Any, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

from app.modules.agent.prompts import CRITIC_PROMPT, SYSTEM_PROMPT


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    # How many critic passes have run — the critic gets exactly one shot at
    # sending the answer back, otherwise a stubborn model could loop forever.
    critique_rounds: int


def _serialize(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


_CRITIC_FENCE_RE = re.compile(r"^```(?:json)?|```$", re.IGNORECASE | re.MULTILINE)


def parse_critic_verdict(content: str) -> tuple[bool, str]:
    """(ok, fix). Anything unparseable counts as approval — the critic is a
    quality net, and a broken net must not block an otherwise fine answer."""
    raw = _CRITIC_FENCE_RE.sub("", content).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return True, ""
    if not isinstance(parsed, dict):
        return True, ""
    ok = parsed.get("ok", True)
    fix = str(parsed.get("fix") or "").strip()
    return (bool(ok) or not fix), fix


def build_agent_graph(
    chat_model: BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str = SYSTEM_PROMPT,
    reminder: str | None = None,
    self_check: bool = False,
) -> CompiledStateGraph:
    """The core loop: model -> tools -> model, looping until the model stops calling tools.

    Tool errors are caught here and fed back as a ToolMessage so the model can react
    instead of the whole request blowing up.

    `reminder` is re-injected as the LAST message before every generation. Instructions
    at the top of the system prompt lose to whatever came most recently — e.g. the
    answer-language directive was ignored once a tool returned a screenful of Russian
    transaction data — so recency-sensitive directives go here, not in system_prompt.

    With `self_check` on, a critic pass reviews the final (tool-free) answer against
    the known failure modes (wrong language, no chart/period on a broad question,
    transfers passed off as spending, raw SQL in the text) and sends it back for ONE
    revision when it fails — a weak model follows a pointed correction far more
    reliably than it follows the original 40-line instruction list.
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

    async def call_critic(state: AgentState) -> dict:
        messages = state["messages"]
        draft = messages[-1]
        question = next(
            (m.content for m in reversed(messages) if isinstance(m, HumanMessage)), ""
        )
        tool_names = ", ".join(
            dict.fromkeys(m.name or "?" for m in messages if isinstance(m, ToolMessage))
        ) or "—"
        prompt = CRITIC_PROMPT.format(
            question=question, tools=tool_names, answer=draft.content
        )
        # The critic judges, it never calls tools — plain model, no binding.
        response = await chat_model.ainvoke(prompt)
        content = response.content if isinstance(response.content, str) else str(response.content)
        ok, fix = parse_critic_verdict(content)
        rounds = state.get("critique_rounds", 0) + 1
        if ok:
            return {"critique_rounds": rounds}
        return {
            "critique_rounds": rounds,
            "messages": [
                SystemMessage(
                    content=(
                        "Контроль качества отклонил твой ответ. Исправь и ответь заново "
                        f"(язык ответа — язык вопроса пользователя): {fix}"
                    )
                )
            ],
        }

    def route_after_agent(state: AgentState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        if self_check and state.get("critique_rounds", 0) < 1:
            return "critic"
        return END

    def route_after_critic(state: AgentState) -> str:
        # The critic leaves a correction SystemMessage only when it rejects.
        if isinstance(state["messages"][-1], SystemMessage):
            return "agent"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", call_tools)
    graph.set_entry_point("agent")
    agent_routes: dict[Hashable, str] = {"tools": "tools", END: END}
    if self_check:
        graph.add_node("critic", call_critic)
        graph.add_conditional_edges("critic", route_after_critic, {"agent": "agent", END: END})
        agent_routes["critic"] = "critic"
    graph.add_conditional_edges("agent", route_after_agent, agent_routes)
    graph.add_edge("tools", "agent")
    return graph.compile()
