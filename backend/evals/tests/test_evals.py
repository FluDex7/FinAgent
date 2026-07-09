from decimal import Decimal

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.modules.agent import service as agent_service_module
from app.modules.agent.service import AgentService
from app.modules.agent.tests.fakes import FakeToolCallingChatModel
from app.modules.categorization.service import match_rule, normalize_merchant
from app.modules.statements.parsers.csv_parser import parse_csv
from evals.dataset import GOLDEN_CASES, JUNE_CSV, MAY_CSV
from evals.runner import AgentTrace, run_case, seed_fixtures
from evals.scoring import aggregate, deterministic_scores

KNOWN_TOOLS = {
    "sql_query",
    "plot_chart",
    "compare_periods",
    "find_subscriptions",
    "rag_lookup",
    "read_document",
    "web_search",
}


def test_dataset_ids_unique_and_tools_are_real():
    ids = [c.id for c in GOLDEN_CASES]
    assert len(ids) == len(set(ids))
    assert len(GOLDEN_CASES) >= 12
    assert {c.language for c in GOLDEN_CASES} == {"ru", "en"}
    for case in GOLDEN_CASES:
        assert case.reference.strip()
        assert set(case.expected_tools) <= KNOWN_TOOLS, case.id
        assert set(case.forbidden_tools) <= KNOWN_TOOLS, case.id


def test_fixture_sums_match_the_references():
    # The golden references quote exact numbers — if someone edits the CSVs,
    # this pins the documented math to the actual fixture content.
    may = parse_csv(MAY_CSV.encode())
    june = parse_csv(JUNE_CSV.encode())

    assert sum(t.amount for t in may if t.amount < 0) == Decimal("-7298.00")
    assert sum(t.amount for t in june if t.amount < 0) == Decimal("-22698.00")
    assert sum(t.amount for t in june if t.amount > 0) == Decimal("20000.00")

    def category_total(rows, category: str) -> Decimal:
        return sum(
            (-t.amount for t in rows if t.amount < 0
             and match_rule(normalize_merchant(t.raw_description)) == category),
            Decimal(0),
        )

    assert category_total(june, "Продукты") == Decimal("10000.00")
    assert category_total(may, "Продукты") == Decimal("5000.00")
    assert category_total(june, "Транспорт") == Decimal("1200.00")
    assert category_total(june, "Кафе и рестораны") == Decimal("2500.00")
    assert category_total(june, "Переводы") == Decimal("5000.00")

    # Every fixture merchant must hit a built-in rule — otherwise seeding
    # would fall back to LLM categorization and stop being deterministic.
    for t in may + june:
        assert match_rule(normalize_merchant(t.raw_description)) is not None, t.raw_description


def test_deterministic_scores_flag_each_failure_mode():
    case = next(c for c in GOLDEN_CASES if c.id == "subscriptions_en")
    good = AgentTrace(
        case_id=case.id,
        question=case.question,
        answer="Two recurring payments: TWINBY 499 ₽/month and REG.RU 299 ₽/month.",
        tools=["find_subscriptions"],
        contexts=["find_subscriptions: [...]"],
    )
    scores = deterministic_scores(case, good)
    assert scores["tools_expected"] == 1.0
    assert scores["tools_forbidden_absent"] == 1.0
    assert scores["language_match"] == 1.0
    assert scores["no_sql_leak"] == 1.0
    assert scores["completed"] == 1.0

    bad = AgentTrace(
        case_id=case.id,
        question=case.question,
        answer=(
            "Вот ваши подписки. SELECT * FROM transactions;\n"
            "| Дата | Сумма |\n|---|---|\n| 2025-06-08 | 499 |"
        ),
        tools=["sql_query"],
    )
    scores = deterministic_scores(case, bad)
    assert scores["tools_expected"] == 0.0
    assert scores["tools_forbidden_absent"] == 0.0
    assert scores["language_match"] == 0.0
    assert scores["no_sql_leak"] == 0.0
    assert scores["no_markdown_table"] == 0.0


def test_chart_check_applies_only_when_expected():
    chart_case = next(c for c in GOLDEN_CASES if c.expect_chart)
    plain_case = next(c for c in GOLDEN_CASES if not c.expect_chart)
    no_chart = AgentTrace(case_id="x", question="q", answer="ответ", has_chart=False)
    assert deterministic_scores(chart_case, no_chart)["chart_present"] == 0.0
    assert deterministic_scores(plain_case, no_chart)["chart_present"] is None


def test_aggregate_skips_not_applicable():
    merged = aggregate(
        {
            "a": {"m": 1.0, "n": None},
            "b": {"m": 0.0, "n": 1.0},
        }
    )
    assert merged == {"m": 0.5, "n": 1.0}


@pytest.fixture
async def session():
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as conn:
        transaction = await conn.begin()
        maker = async_sessionmaker(bind=conn, expire_on_commit=False)
        session = maker()
        yield session
        await session.close()
        await transaction.rollback()
    await engine.dispose()


async def test_seed_and_run_case_collects_a_full_trace(monkeypatch, session, tmp_path):
    # End-to-end through the real service with a canned model: fixtures seed
    # through the actual upload pipeline, and run_case gathers answer/tools/
    # contexts/chart exactly as scoring expects them.
    service = AgentService(session, Settings(statements_dir=str(tmp_path), agent_self_check=False))
    await seed_fixtures(service.statements)

    scope_json = AIMessage(content='{"files": ["2025"], "explanation": "все данные"}')
    tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "plot_chart",
                "args": {"kind": "donut", "data": [{"label": "Продукты", "value": 10000}]},
                "id": "call1",
            }
        ],
    )
    final = AIMessage(content="Больше всего вы тратите на продукты — 10 000 ₽.")
    fake = FakeToolCallingChatModel(responses=[scope_json, tool_call, final])
    monkeypatch.setattr(agent_service_module, "get_chat_model", lambda settings: fake)

    case = next(c for c in GOLDEN_CASES if c.id == "broad_spending_ru")
    trace = await run_case(service, case)

    assert trace.error is None
    assert "продукты" in trace.answer.lower()
    assert trace.tools == ["plot_chart"]
    assert trace.has_chart is True
    assert trace.contexts and trace.contexts[0].startswith("plot_chart:")

    scores = deterministic_scores(case, trace)
    assert scores["chart_present"] == 1.0
    assert scores["language_match"] == 1.0
