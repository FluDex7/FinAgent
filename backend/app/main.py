from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import AppError
from app.core.health import CheckResult, run_health_checks
from app.core.logging import print_health_banner, setup_logging
from app.core.schemas import CamelModel
from app.modules.agent.router import router as agent_router
from app.modules.categorization.router import router as categorization_router
from app.modules.statements.router import router as statements_router

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    results = await run_health_checks(engine, settings)
    print_health_banner(results, ui_url="http://localhost:8000")
    yield


app = FastAPI(title="FinAgent", lifespan=lifespan)
app.include_router(statements_router)
app.include_router(agent_router)
app.include_router(categorization_router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    content = {"detail": exc.message, "hint": exc.hint}
    return JSONResponse(status_code=exc.status_code, content=content)


class ServiceStatus(CamelModel):
    ok: bool
    detail: str


class LlmStatus(CamelModel):
    provider: str
    ok: bool
    model: str
    detail: str


class HealthResponse(CamelModel):
    llm: LlmStatus
    postgres: ServiceStatus
    qdrant: ServiceStatus
    tesseract: ServiceStatus
    statements_dir: ServiceStatus


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
