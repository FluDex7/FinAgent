from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.core.health import (
    check_llm_provider,
    check_mlflow,
    check_postgres,
    check_qdrant,
    check_statements_dir,
    check_tesseract,
    check_web_search,
)


def make_settings(**overrides) -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://finagent:finagent@localhost:5432/finagent",
        **overrides,
    )


async def test_check_postgres_ok():
    engine = create_async_engine(make_settings().database_url)
    result = await check_postgres(engine, make_settings())
    assert result.ok is True
    await engine.dispose()


async def test_check_postgres_unreachable():
    engine = create_async_engine(
        "postgresql+asyncpg://finagent:finagent@localhost:59999/finagent"
    )
    result = await check_postgres(engine, make_settings())
    assert result.ok is False
    assert result.hint
    await engine.dispose()


async def test_check_qdrant_unreachable():
    settings = make_settings(qdrant_url="http://localhost:1")
    result = await check_qdrant(settings)
    assert result.ok is False


async def test_check_llm_provider_openai_missing_key():
    settings = make_settings(llm_provider="openai", openai_api_key=None)
    result = await check_llm_provider(settings)
    assert result.ok is False
    assert "OPENAI_API_KEY" in result.detail


async def test_check_llm_provider_openai_with_key():
    settings = make_settings(llm_provider="openai", openai_api_key="sk-test")
    result = await check_llm_provider(settings)
    assert result.ok is True


async def test_check_llm_provider_ollama_unreachable():
    settings = make_settings(llm_provider="ollama", ollama_host="http://localhost:1")
    result = await check_llm_provider(settings)
    assert result.ok is False


async def test_check_llm_provider_ollama_reachable():
    settings = make_settings(llm_provider="ollama", ollama_host="http://localhost:11434")
    fake_response = AsyncMock()
    fake_response.raise_for_status = lambda: None
    with patch("httpx.AsyncClient.get", return_value=fake_response):
        result = await check_llm_provider(settings)
    assert result.ok is True


def test_check_statements_dir_creates_and_counts(tmp_path):
    target = tmp_path / "statements"
    (target / "2025").mkdir(parents=True)
    (target / "2025" / "q1.csv").write_text("a,b\n1,2\n")
    settings = make_settings(statements_dir=str(target))
    result = check_statements_dir(settings)
    assert result.ok is True
    assert "1" in result.detail


def test_check_tesseract_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    result = check_tesseract()
    assert result.ok is False
    assert result.hint


def test_check_mlflow_reports_configured_uri():
    settings = make_settings(
        mlflow_tracking_uri="sqlite:///./mlflow.db", mlflow_experiment_name="finagent"
    )
    result = check_mlflow(settings)
    assert result.ok is True
    assert "mlflow.db" in result.detail
    assert "finagent" in result.detail


def test_check_web_search_ok_when_disabled():
    # Optional feature — a missing key is never an environment "problem".
    settings = make_settings(tavily_api_key=None)
    result = check_web_search(settings)
    assert result.ok is True
    assert "отключён" in result.detail


def test_check_web_search_ok_when_configured():
    settings = make_settings(tavily_api_key="tvly-test")
    result = check_web_search(settings)
    assert result.ok is True
    assert "Tavily" in result.detail
