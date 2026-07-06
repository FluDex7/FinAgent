import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.exceptions import SqlValidationError
from app.modules.tools.sql_query import build_sql_query_tool, generate_sql, run_sql_query
from app.modules.transactions.schemas import TransactionIn
from app.modules.transactions.service import TransactionsService

CATEGORY_ID = "11111111-1111-1111-1111-111111111111"
STATEMENT_ID = "22222222-2222-2222-2222-222222222222"


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
async def transactions_service(session):
    from sqlalchemy import text

    await session.execute(
        text(
            "INSERT INTO statements (id, filename, folder_path, source_format, status, "
            "transaction_count) VALUES (:id, 'q1.csv', '2025', 'csv', 'parsed', 0)"
        ),
        {"id": STATEMENT_ID},
    )
    service = TransactionsService(session)
    await service.bulk_create(
        STATEMENT_ID,
        [
            TransactionIn(date="2025-01-14", amount="-540.00", raw_description="PYATEROCHKA"),
            TransactionIn(date="2025-01-15", amount="-1200.50", raw_description="YANDEX.TAXI"),
        ],
    )
    return service


async def test_generate_sql_strips_code_fence():
    fake_model = FakeListChatModel(responses=["```sql\nSELECT 1\n```"])
    sql = await generate_sql(fake_model, "test", None)
    assert sql == "SELECT 1"


async def test_run_sql_query_executes_generated_sql(transactions_service):
    sql = f"SELECT SUM(amount) AS total FROM transactions WHERE statement_id = '{STATEMENT_ID}'"
    fake_model = FakeListChatModel(responses=[sql])
    outcome = await run_sql_query(
        transactions_service=transactions_service,
        chat_model=fake_model,
        question="Сколько всего потрачено?",
    )
    assert "LIMIT" in outcome.sql.upper()
    assert float(outcome.rows[0]["total"]) == pytest.approx(-1740.50)


async def test_run_sql_query_rejects_skip_response_with_clear_error(transactions_service):
    # The SQL-generation prompt tells the sub-LLM to answer "SKIP" for questions it
    # can't handle with one query (e.g. subscriptions) — that must surface as a clear
    # tool error, not get passed through to validate_and_cap as garbage SQL.
    fake_model = FakeListChatModel(responses=["SKIP"])
    with pytest.raises(SqlValidationError):
        await run_sql_query(
            transactions_service=transactions_service,
            chat_model=fake_model,
            question="найди подписки",
        )


async def test_run_sql_query_rejects_unsafe_generated_sql(transactions_service):
    fake_model = FakeListChatModel(responses=["DROP TABLE transactions"])
    with pytest.raises(SqlValidationError):
        await run_sql_query(
            transactions_service=transactions_service,
            chat_model=fake_model,
            question="что угодно",
        )


async def test_bad_sql_does_not_poison_the_session_for_later_queries(transactions_service):
    # A runtime DB error (e.g. a non-UUID literal against a uuid column) must be
    # contained to a savepoint — without one, Postgres aborts the whole transaction
    # and every later query on the same session (including persisting the chat
    # message) fails too, which is exactly what silently killed a real chat turn.
    with pytest.raises(Exception):  # noqa: B017 - asyncpg's own DBAPI error class
        await transactions_service.run_validated_sql(
            "SELECT * FROM transactions WHERE statement_id = 'not-a-uuid'"
        )

    rows = await transactions_service.run_validated_sql(
        f"SELECT COUNT(*) AS n FROM transactions WHERE statement_id = '{STATEMENT_ID}'"
    )
    assert rows[0]["n"] == 2


async def test_build_sql_query_tool_end_to_end(transactions_service):
    fake_model = FakeListChatModel(
        responses=[f"SELECT COUNT(*) AS n FROM transactions WHERE statement_id = '{STATEMENT_ID}'"]
    )
    tool = build_sql_query_tool(transactions_service, fake_model)
    result = await tool.ainvoke({"question": "Сколько транзакций?"})
    assert result["rows"][0]["n"] == 2
