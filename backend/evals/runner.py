"""Seeds the fixture statements and drives the real agent, case by case."""

from dataclasses import dataclass, field

from app.modules.agent.service import AgentService
from app.modules.statements.service import StatementsService
from evals.dataset import FIXTURE_FILES, GoldenCase


@dataclass
class AgentTrace:
    case_id: str
    question: str
    answer: str = ""
    tools: list[str] = field(default_factory=list)
    # Tool outputs the answer should be grounded in (Ragas faithfulness contexts).
    contexts: list[str] = field(default_factory=list)
    has_chart: bool = False
    error: str | None = None


async def seed_fixtures(statements: StatementsService) -> None:
    """Uploads the fixture CSVs through the real pipeline — parsing, auto-rename
    and rule-based categorization run exactly as they would for a live user."""
    for filename, folder, content in FIXTURE_FILES:
        await statements.upload(filename=filename, folder=folder, content=content.encode())


async def run_case(service: AgentService, case: GoldenCase) -> AgentTrace:
    trace = AgentTrace(case_id=case.id, question=case.question)
    async for event in service.stream_chat(None, case.question, []):
        kind = event["event"]
        if kind == "token":
            trace.answer += event["data"]["text"]
        elif kind == "tool_end":
            name = event["data"]["name"]
            trace.tools.append(name)
            detail = event["data"].get("detail")
            # self_check is the critic's own verdict, not data the answer is based on.
            if detail and name != "self_check":
                trace.contexts.append(f"{name}: {detail}")
        elif kind == "block":
            trace.has_chart = True
        elif kind == "error":
            trace.error = event["data"]["message"]
    return trace
