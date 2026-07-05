import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.modules.statements.service import StatementsService
from app.modules.tools.read_document import build_read_document_tool

CSV_CONTENT = b"date,amount,description\n2025-01-14,-540.00,PYATEROCHKA 5443\n"


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
def statements_service(session, tmp_path) -> StatementsService:
    return StatementsService(session, Settings(statements_dir=str(tmp_path)))


async def test_read_document_tool_returns_file_content(statements_service):
    await statements_service.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)
    tool = build_read_document_tool(statements_service)

    result = await tool.ainvoke({"path": "2025/q1"})

    assert "PYATEROCHKA" in result


async def test_read_document_tool_reports_missing_file_gracefully(statements_service):
    tool = build_read_document_tool(statements_service)

    result = await tool.ainvoke({"path": "2025/does-not-exist"})

    assert "Не удалось прочитать" in result


async def test_read_document_tool_truncates_long_text(statements_service, monkeypatch):
    from app.modules.tools import read_document as read_document_module

    monkeypatch.setattr(read_document_module, "MAX_CHARS", 10)
    await statements_service.upload(filename="q1.csv", folder="2025", content=CSV_CONTENT)
    tool = build_read_document_tool(statements_service)

    result = await tool.ainvoke({"path": "2025/q1"})

    assert result.endswith("…(текст обрезан)")
