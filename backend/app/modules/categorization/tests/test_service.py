import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.modules.categorization import service as categorization_service_module
from app.modules.categorization.service import (
    CategorizationService,
    match_rule,
    normalize_merchant,
)
from app.modules.transactions.schemas import TransactionIn
from app.modules.transactions.service import TransactionsService

STATEMENT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


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
    return TransactionsService(session)


@pytest.fixture
def categorization_service(transactions_service) -> CategorizationService:
    return CategorizationService(transactions_service, Settings())


def test_normalize_merchant_strips_trailing_digits_and_city():
    assert normalize_merchant("PYATEROCHKA 24281 Kazan RUS") == "PYATEROCHKA"
    assert normalize_merchant("YANDEX.TAXI") == "YANDEX.TAXI"


def test_match_rule_finds_known_merchant():
    assert match_rule("PYATEROCHKA") == "Продукты"
    assert match_rule("YANDEX.TAXI") == "Транспорт"
    assert match_rule("SOME UNKNOWN SHOP") is None


async def test_rule_matched_merchant_gets_categorized(
    categorization_service: CategorizationService, transactions_service: TransactionsService
):
    rows = await transactions_service.bulk_create(
        STATEMENT_ID,
        [TransactionIn(date="2025-01-14", amount="-540.00", raw_description="PYATEROCHKA 5443")],
    )

    await categorization_service.categorize_transactions(rows)

    transactions = await transactions_service.list_by_statement(STATEMENT_ID)
    assert transactions[0].category_id is not None
    categories = await transactions_service.list_categories()
    category = next(c for c in categories if c.id == transactions[0].category_id)
    assert category.name == "Продукты"


async def test_repeated_merchant_reuses_cached_merchant_row(
    categorization_service: CategorizationService, transactions_service: TransactionsService
):
    rows = await transactions_service.bulk_create(
        STATEMENT_ID,
        [
            TransactionIn(date="2025-01-14", amount="-540.00", raw_description="PYATEROCHKA 5443"),
            TransactionIn(date="2025-01-15", amount="-100.00", raw_description="PYATEROCHKA 24281"),
        ],
    )

    await categorization_service.categorize_transactions(rows)

    transactions = await transactions_service.list_by_statement(STATEMENT_ID)
    assert transactions[0].merchant_id == transactions[1].merchant_id


async def test_unknown_merchant_falls_back_to_llm_then_prochee_on_failure(
    categorization_service: CategorizationService, transactions_service: TransactionsService
):
    # Settings() has no OPENAI_API_KEY, so the LLM call fails and this must not raise.
    rows = await transactions_service.bulk_create(
        STATEMENT_ID,
        [TransactionIn(date="2025-01-14", amount="-10.00", raw_description="TOTALLY UNKNOWN SHOP")],
    )

    await categorization_service.categorize_transactions(rows)

    transactions = await transactions_service.list_by_statement(STATEMENT_ID)
    categories = await transactions_service.list_categories()
    category = next(c for c in categories if c.id == transactions[0].category_id)
    assert category.name == "Прочее"


async def test_unknown_merchant_uses_llm_classification_when_available(
    monkeypatch,
    categorization_service: CategorizationService,
    transactions_service: TransactionsService,
):
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    fake = FakeListChatModel(responses=['{"NOVAYA KOFEYNYA": "Кафе и рестораны"}'])
    monkeypatch.setattr(categorization_service_module, "get_chat_model", lambda settings: fake)

    rows = await transactions_service.bulk_create(
        STATEMENT_ID,
        [TransactionIn(date="2025-01-14", amount="-10.00", raw_description="NOVAYA KOFEYNYA")],
    )

    await categorization_service.categorize_transactions(rows)

    transactions = await transactions_service.list_by_statement(STATEMENT_ID)
    categories = await transactions_service.list_categories()
    category = next(c for c in categories if c.id == transactions[0].category_id)
    assert category.name == "Кафе и рестораны"

    merchant = await transactions_service.get_merchant("NOVAYA KOFEYNYA")
    assert merchant is not None


async def test_empty_transaction_list_is_a_no_op(categorization_service: CategorizationService):
    await categorization_service.categorize_transactions([])
