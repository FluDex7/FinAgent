import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.exceptions import PathTraversalError, StatementNotFoundError
from app.modules.statements.service import StatementsService

CSV_CONTENT = (
    b"date,amount,description\n"
    b"2025-01-14,-540.00,PYATEROCHKA 5443\n"
    b"2025-01-15,-1200.50,YANDEX.TAXI\n"
)


@pytest.fixture
async def session():
    # A dedicated engine per test avoids asyncpg connections bound to a
    # previous test's (now closed) event loop.
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
def statements_dir(tmp_path):
    return tmp_path


@pytest.fixture
def service(session: AsyncSession, statements_dir) -> StatementsService:
    settings = Settings(statements_dir=str(statements_dir))
    return StatementsService(session, settings)


async def test_browse_tree_empty(service: StatementsService):
    assert await service.browse_tree() == []


async def test_upload_csv_creates_parsed_statement_and_transactions(service: StatementsService):
    statement = await service.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)

    assert statement.status.value == "parsed"
    assert statement.transaction_count == 2
    assert statement.date_from is not None
    assert statement.date_to is not None
    assert statement.date_from.isoformat() == "2025-01-14"
    assert statement.date_to.isoformat() == "2025-01-15"

    transactions = await service.list_transactions(statement.id)
    assert len(transactions) == 2


async def test_upload_bad_csv_marks_error_but_keeps_statement(service: StatementsService):
    statement = await service.upload(
        filename="bad.csv", folder="2025", content=b"not,a,valid\nfile"
    )
    assert statement.status.value == "error"
    assert statement.error_message


async def test_upload_unsupported_extension_raises(service: StatementsService):
    from app.core.exceptions import StatementParseError

    with pytest.raises(StatementParseError):
        await service.upload(filename="statement.txt", folder="2025", content=b"hello")


async def test_browse_tree_reflects_disk_and_db_status(service: StatementsService):
    await service.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)
    (service.root / "2025" / "not_yet_parsed.csv").write_bytes(CSV_CONTENT)

    tree = await service.browse_tree()
    assert len(tree) == 1
    folder = tree[0]
    assert folder.name == "2025"
    names_status = {f.name: f.status.value for f in folder.files}
    assert names_status["q1"] == "parsed"
    assert names_status["not_yet_parsed"] == "new"


async def test_browse_tree_with_path_returns_single_folder(service: StatementsService):
    await service.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)
    await service.upload(filename="q2.csv", folder="2024", content=CSV_CONTENT)

    tree = await service.browse_tree("2025")
    assert len(tree) == 1
    assert tree[0].name == "2025"
    assert [f.name for f in tree[0].files] == ["q1"]


async def test_browse_tree_path_traversal_rejected(service: StatementsService):
    with pytest.raises(PathTraversalError):
        await service.browse_tree("../../etc")


async def test_get_statement_not_found_raises(service: StatementsService):
    import uuid

    with pytest.raises(StatementNotFoundError):
        await service.get(uuid.uuid4())


async def test_delete_removes_file_and_db_row(service: StatementsService):
    statement = await service.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)
    file_path = service.root / "2025" / "q1.csv"
    assert file_path.exists()

    await service.delete(statement.id)

    assert not file_path.exists()
    with pytest.raises(StatementNotFoundError):
        await service.get(statement.id)


async def test_resolve_paths_whole_folder_returns_all_parsed_files(service: StatementsService):
    q1 = await service.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)
    q2 = await service.upload(filename="q2.csv", folder="2025", content=CSV_CONTENT)

    ids = await service.resolve_paths_to_statement_ids(["2025"])

    assert set(ids) == {str(q1.id), str(q2.id)}


async def test_resolve_paths_single_file(service: StatementsService):
    q1 = await service.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)
    await service.upload(filename="q2.csv", folder="2025", content=CSV_CONTENT)

    ids = await service.resolve_paths_to_statement_ids(["2025/q1"])

    assert ids == [str(q1.id)]


async def test_resolve_paths_skips_unparsed_files(service: StatementsService):
    (service.root / "2025").mkdir(parents=True)
    (service.root / "2025" / "not_parsed.csv").write_bytes(CSV_CONTENT)

    ids = await service.resolve_paths_to_statement_ids(["2025"])

    assert ids == []


async def test_read_raw_text_returns_csv_content(service: StatementsService):
    await service.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)

    text = await service.read_raw_text("2025/q1")

    assert "PYATEROCHKA" in text


async def test_read_raw_text_root_level_file(service: StatementsService):
    (service.root / "апрель.csv").write_bytes(CSV_CONTENT)

    text = await service.read_raw_text("апрель")

    assert "YANDEX.TAXI" in text


async def test_read_raw_text_unknown_file_raises(service: StatementsService):
    with pytest.raises(StatementNotFoundError):
        await service.read_raw_text("2025/nonexistent")


async def test_read_raw_text_unsupported_extension_raises(service: StatementsService):
    (service.root / "notes.txt").write_bytes(b"hello")

    from app.core.exceptions import StatementParseError

    with pytest.raises(StatementParseError):
        await service.read_raw_text("notes")


async def test_read_raw_text_pdf_via_native_extraction(service: StatementsService):
    from pathlib import Path

    fixture = (
        Path(__file__).parent / "fixtures" / "pdf_samples" / "tbank_funds_movement.pdf"
    )
    (service.root / "tbank.pdf").write_bytes(fixture.read_bytes())

    text = await service.read_raw_text("tbank")

    assert "ТБАНК" in text.upper()


def _pdf_fixture(name: str) -> bytes:
    from pathlib import Path

    return (
        Path(__file__).parent / "fixtures" / "pdf_samples" / f"{name}.pdf"
    ).read_bytes()


async def test_upload_pdf_auto_renames_to_bank_period(service: StatementsService):
    content = _pdf_fixture("tbank_funds_movement")

    statement = await service.upload(filename="random_name.pdf", folder="2026", content=content)

    assert statement.filename == "тбанк_2026-06.pdf"
    assert (service.root / "2026" / "тбанк_2026-06.pdf").exists()
    assert not (service.root / "2026" / "random_name.pdf").exists()


async def test_upload_sberbank_pdf_auto_renames(service: StatementsService):
    content = _pdf_fixture("sberbank_account_statement")

    statement = await service.upload(filename="whatever.pdf", folder="", content=content)

    assert statement.filename == "сбербанк_2024-06.pdf"


async def test_upload_pdf_rename_avoids_collision(service: StatementsService):
    content = _pdf_fixture("tbank_funds_movement")
    (service.root / "2026").mkdir(parents=True)
    (service.root / "2026" / "тбанк_2026-06.pdf").write_bytes(b"existing file")

    statement = await service.upload(filename="another.pdf", folder="2026", content=content)

    assert statement.filename == "тбанк_2026-06-2.pdf"


async def test_csv_upload_is_not_renamed(service: StatementsService):
    statement = await service.upload(filename="my_export.csv", folder="2025", content=CSV_CONTENT)

    assert statement.filename == "my_export.csv"
