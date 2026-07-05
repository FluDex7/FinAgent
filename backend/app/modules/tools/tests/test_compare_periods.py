import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.modules.tools.compare_periods import build_compare_periods_tool, compare_periods
from app.modules.transactions.schemas import TransactionIn
from app.modules.transactions.service import TransactionsService

STATEMENT_A = uuid.UUID("44444444-4444-4444-4444-444444444444")
STATEMENT_B = uuid.UUID("55555555-5555-5555-5555-555555555555")


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
    for statement_id, folder in ((STATEMENT_A, "2025-02"), (STATEMENT_B, "2025-03")):
        await session.execute(
            text(
                "INSERT INTO statements (id, filename, folder_path, source_format, status, "
                "transaction_count) VALUES (:id, 'q.csv', :folder, 'csv', 'parsed', 0)"
            ),
            {"id": statement_id, "folder": folder},
        )
    return TransactionsService(session)


async def _seed_category(transactions_service: TransactionsService, name: str) -> uuid.UUID:
    category = await transactions_service.get_or_create_category(name)
    return category.id


async def test_compare_periods_computes_deltas_and_biggest_driver(
    transactions_service: TransactionsService,
):
    cafe_id = await _seed_category(transactions_service, "Кафе и рестораны")
    products_id = await _seed_category(transactions_service, "Продукты")

    a_rows = await transactions_service.bulk_create(
        STATEMENT_A,
        [
            TransactionIn(date="2025-02-01", amount="-1000.00", raw_description="Кафе А"),
            TransactionIn(date="2025-02-02", amount="-5000.00", raw_description="Продукты А"),
        ],
    )
    await transactions_service.set_transaction_category(a_rows[0].id, None, cafe_id)
    await transactions_service.set_transaction_category(a_rows[1].id, None, products_id)

    b_rows = await transactions_service.bulk_create(
        STATEMENT_B,
        [
            TransactionIn(date="2025-03-01", amount="-3000.00", raw_description="Кафе Б"),
            TransactionIn(date="2025-03-02", amount="-5200.00", raw_description="Продукты Б"),
        ],
    )
    await transactions_service.set_transaction_category(b_rows[0].id, None, cafe_id)
    await transactions_service.set_transaction_category(b_rows[1].id, None, products_id)

    result = await compare_periods(
        transactions_service, [str(STATEMENT_A)], [str(STATEMENT_B)]
    )

    assert result["totalA"] == pytest.approx(6000.0)
    assert result["totalB"] == pytest.approx(8200.0)
    assert result["totalDelta"] == pytest.approx(2200.0)
    assert result["biggestDriver"] == "Кафе и рестораны"

    cafe_row = next(c for c in result["categories"] if c["category"] == "Кафе и рестораны")
    assert cafe_row["periodA"] == pytest.approx(1000.0)
    assert cafe_row["periodB"] == pytest.approx(3000.0)
    assert cafe_row["delta"] == pytest.approx(2000.0)
    assert cafe_row["growthPercent"] == pytest.approx(200.0)


async def test_compare_periods_ignores_income_transactions(
    transactions_service: TransactionsService,
):
    products_id = await _seed_category(transactions_service, "Продукты")

    rows = await transactions_service.bulk_create(
        STATEMENT_A,
        [
            TransactionIn(date="2025-02-01", amount="-1000.00", raw_description="Продукты"),
            TransactionIn(date="2025-02-05", amount="+50000.00", raw_description="Зарплата"),
        ],
    )
    await transactions_service.set_transaction_category(rows[0].id, None, products_id)

    result = await compare_periods(transactions_service, [str(STATEMENT_A)], [])

    assert result["totalA"] == pytest.approx(1000.0)


async def test_compare_periods_handles_no_prior_spending_without_division_error(
    transactions_service: TransactionsService,
):
    products_id = await _seed_category(transactions_service, "Продукты")
    rows = await transactions_service.bulk_create(
        STATEMENT_B,
        [TransactionIn(date="2025-03-01", amount="-500.00", raw_description="Продукты")],
    )
    await transactions_service.set_transaction_category(rows[0].id, None, products_id)

    result = await compare_periods(transactions_service, [], [str(STATEMENT_B)])

    row = result["categories"][0]
    assert row["growthPercent"] is None
    assert row["periodA"] == 0.0


async def test_build_compare_periods_tool_end_to_end(transactions_service: TransactionsService):
    products_id = await _seed_category(transactions_service, "Продукты")
    rows = await transactions_service.bulk_create(
        STATEMENT_A,
        [TransactionIn(date="2025-02-01", amount="-100.00", raw_description="Продукты")],
    )
    await transactions_service.set_transaction_category(rows[0].id, None, products_id)

    tool = build_compare_periods_tool(transactions_service)
    result = await tool.ainvoke(
        {"period_a_statement_ids": [str(STATEMENT_A)], "period_b_statement_ids": []}
    )

    assert result["totalA"] == pytest.approx(100.0)
