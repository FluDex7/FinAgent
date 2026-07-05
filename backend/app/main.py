from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings
from app.core.database import engine
from app.core.health import CheckResult, run_health_checks
from app.core.logging import print_health_banner, setup_logging

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    results = await run_health_checks(engine, settings)
    print_health_banner(results, ui_url="http://localhost:8000")
    yield


app = FastAPI(title="FinAgent", lifespan=lifespan)


class ServiceStatus(BaseModel):
    ok: bool
    detail: str


class LlmStatus(BaseModel):
    provider: str
    ok: bool
    model: str
    detail: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    llm: LlmStatus
    postgres: ServiceStatus
    qdrant: ServiceStatus
    tesseract: ServiceStatus
    statements_dir: ServiceStatus = Field(serialization_alias="statementsDir")


def _find(results: list[CheckResult], name: str) -> CheckResult:
    return next(r for r in results if r.name == name)


@app.get("/health", response_model=HealthResponse, response_model_by_alias=True)
async def health() -> HealthResponse:
    results = await run_health_checks(engine, settings)
    llm_result = _find(results, "LLM-провайдер")
    postgres_result = _find(results, "PostgreSQL")
    qdrant_result = _find(results, "Qdrant")
    tesseract_result = _find(results, "Tesseract OCR")
    statements_result = _find(results, "Папка выписок")
    model = settings.openai_model if settings.llm_provider == "openai" else settings.ollama_model

    return HealthResponse(
        llm=LlmStatus(
            provider=settings.llm_provider,
            ok=llm_result.ok,
            model=model,
            detail=llm_result.detail,
        ),
        postgres=ServiceStatus(ok=postgres_result.ok, detail=postgres_result.detail),
        qdrant=ServiceStatus(ok=qdrant_result.ok, detail=qdrant_result.detail),
        tesseract=ServiceStatus(ok=tesseract_result.ok, detail=tesseract_result.detail),
        statements_dir=ServiceStatus(ok=statements_result.ok, detail=statements_result.detail),
    )
