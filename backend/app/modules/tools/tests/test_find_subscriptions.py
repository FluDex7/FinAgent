import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.modules.tools.find_subscriptions import build_find_subscriptions_tool, find_subscriptions
from app.modules.transactions.models import MerchantSource
from app.modules.transactions.schemas import TransactionIn
from app.modules.transactions.service import TransactionsService

STATEMENT_ID = uuid.UUID("66666666-6666-6666-6666-666666666601")


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
    await session.execute(
        text(
            "INSERT INTO statements (id, filename, folder_path, source_format, status, "
            "transaction_count) VALUES (:id, 'q.csv', '2025', 'csv', 'parsed', 0)"
        ),
        {"id": STATEMENT_ID},
    )
    return TransactionsService(session)


async def _seed_merchant_transaction(
    service: TransactionsService, *, merchant_key: str, date: str, amount: str
) -> None:
    category = await service.get_or_create_category("Подписки")
    merchant_id = await service.upsert_merchant(merchant_key, category.id, MerchantSource.rule)
    rows = await service.bulk_create(
        STATEMENT_ID, [TransactionIn(date=date, amount=amount, raw_description=merchant_key)]
    )
    await service.set_transaction_category(rows[0].id, merchant_id, category.id)


async def test_finds_merchant_recurring_across_months_with_stable_amount(
    transactions_service: TransactionsService,
):
    for date in ("2025-01-05", "2025-02-05", "2025-03-05"):
        await _seed_merchant_transaction(
            transactions_service, merchant_key="NETFLIX.COM", date=date, amount="-599.00"
        )

    result = await find_subscriptions(transactions_service)

    assert len(result) == 1
    assert result[0]["merchant"] == "NETFLIX.COM"
    assert result[0]["distinctMonths"] == 3
    assert result[0]["avgAmount"] == pytest.approx(599.0)


async def test_ignores_one_off_merchant(transactions_service: TransactionsService):
    await _seed_merchant_transaction(
        transactions_service, merchant_key="PYATEROCHKA", date="2025-01-05", amount="-540.00"
    )

    result = await find_subscriptions(transactions_service)

    assert result == []


async def test_ignores_merchant_with_wildly_varying_amounts(
    transactions_service: TransactionsService,
):
    # Same merchant across months, but amounts vary too much to look like a fixed
    # subscription fee (e.g. a grocery store visited monthly is not a subscription).
    for date, amount in [("2025-01-05", "-200.00"), ("2025-02-05", "-4000.00")]:
        await _seed_merchant_transaction(
            transactions_service, merchant_key="MAGNIT", date=date, amount=amount
        )

    result = await find_subscriptions(transactions_service)

    assert result == []


async def test_build_find_subscriptions_tool_end_to_end(
    transactions_service: TransactionsService,
):
    for date in ("2025-01-10", "2025-02-10"):
        await _seed_merchant_transaction(
            transactions_service, merchant_key="SPOTIFY", date=date, amount="-299.00"
        )

    tool = build_find_subscriptions_tool(transactions_service)
    result = await tool.ainvoke({})

    assert len(result) == 1
    assert result[0]["merchant"] == "SPOTIFY"
