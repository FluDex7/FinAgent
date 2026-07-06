import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.exceptions import CategoryNotFoundError, MerchantNotFoundError
from app.modules.transactions.models import MerchantSource
from app.modules.transactions.schemas import TransactionIn
from app.modules.transactions.service import TransactionsService

STATEMENT_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")


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
async def service(session) -> TransactionsService:
    await session.execute(
        text(
            "INSERT INTO statements (id, filename, folder_path, source_format, status, "
            "transaction_count) VALUES (:id, 'q.csv', '2025', 'csv', 'parsed', 0)"
        ),
        {"id": STATEMENT_ID},
    )
    return TransactionsService(session)


async def test_list_merchants_filters_needs_review(service: TransactionsService):
    misc = await service.get_or_create_category("Прочее")
    await service.upsert_merchant("RULE_MATCHED", misc.id, MerchantSource.rule)
    await service.upsert_merchant("LLM_GUESSED", misc.id, MerchantSource.llm)
    await service.upsert_merchant("USER_CONFIRMED", misc.id, MerchantSource.user)

    all_merchants = await service.list_merchants()
    needing_review = await service.list_merchants(needs_review=True)

    all_keys = {m.normalized_key for m in all_merchants}
    review_keys = {m.normalized_key for m in needing_review}
    assert {"RULE_MATCHED", "LLM_GUESSED", "USER_CONFIRMED"} <= all_keys
    assert "LLM_GUESSED" in review_keys
    assert "RULE_MATCHED" not in review_keys
    assert "USER_CONFIRMED" not in review_keys


async def test_recategorize_merchant_updates_existing_transactions(
    service: TransactionsService,
):
    misc = await service.get_or_create_category("Прочее")
    cafe = await service.get_or_create_category("Кафе и рестораны")
    merchant_id = await service.upsert_merchant("NOVAYA KOFEYNYA", misc.id, MerchantSource.llm)

    rows = await service.bulk_create(
        STATEMENT_ID,
        [TransactionIn(date="2025-01-14", amount="-10.00", raw_description="NOVAYA KOFEYNYA")],
    )
    await service.set_transaction_category(rows[0].id, merchant_id, misc.id)

    updated = await service.recategorize_merchant(merchant_id, cafe.id)

    assert updated.category_id == cafe.id
    assert updated.source == MerchantSource.user

    transactions = await service.list_by_statement(STATEMENT_ID)
    assert transactions[0].category_id == cafe.id

    # no longer "needs review" — a user just confirmed it
    review = await service.list_merchants(needs_review=True)
    assert merchant_id not in [m.id for m in review]


async def test_list_merchants_includes_transaction_count_and_sample(
    service: TransactionsService,
):
    misc = await service.get_or_create_category("Прочее")
    merchant_id = await service.upsert_merchant("KAZANMETRO", misc.id, MerchantSource.llm)
    rows = await service.bulk_create(
        STATEMENT_ID,
        [
            TransactionIn(date="2025-01-14", amount="-10.00", raw_description="KAZANMETRO 5443"),
            TransactionIn(date="2025-01-15", amount="-20.00", raw_description="KAZANMETRO 5443"),
        ],
    )
    for row in rows:
        await service.set_transaction_category(row.id, merchant_id, misc.id)

    merchants = await service.list_merchants(needs_review=True)
    merchant = next(m for m in merchants if m.id == merchant_id)

    assert merchant.transaction_count == 2
    assert merchant.sample_description == "KAZANMETRO 5443"


async def test_recategorize_unknown_merchant_raises(service: TransactionsService):
    category = await service.get_or_create_category("Прочее")
    with pytest.raises(MerchantNotFoundError):
        await service.recategorize_merchant(uuid.uuid4(), category.id)


async def test_recategorize_with_unknown_category_raises(service: TransactionsService):
    misc = await service.get_or_create_category("Прочее")
    merchant_id = await service.upsert_merchant("SOME SHOP", misc.id, MerchantSource.llm)

    with pytest.raises(CategoryNotFoundError):
        await service.recategorize_merchant(merchant_id, uuid.uuid4())


async def test_update_category_renames_and_recolors(service: TransactionsService):
    category = await service.get_or_create_category("Черновая категория")

    updated = await service.update_category(category.id, name="Новое имя", color="#123456")

    assert updated.name == "Новое имя"
    assert updated.color == "#123456"


async def test_update_unknown_category_raises(service: TransactionsService):
    with pytest.raises(CategoryNotFoundError):
        await service.update_category(uuid.uuid4(), name="x")
