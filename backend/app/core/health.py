import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings

Lang = Literal["ru", "en"]


def _t(lang: Lang, ru: str, en: str) -> str:
    return ru if lang == "ru" else en


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    hint: str | None = None
    # Stable machine id — display names are localized, so lookups go by key.
    key: str = ""


async def check_postgres(
    engine: AsyncEngine, settings: Settings, lang: Lang = "ru"
) -> CheckResult:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return CheckResult(
            "PostgreSQL", True, _t(lang, "подключено", "connected"), key="postgres"
        )
    except Exception as exc:
        return CheckResult(
            "PostgreSQL",
            False,
            _t(
                lang,
                f"недоступен ({exc.__class__.__name__})",
                f"unreachable ({exc.__class__.__name__})",
            ),
            _t(
                lang,
                "проверьте DATABASE_URL в .env и что сервис поднят: docker compose up -d postgres",
                "check DATABASE_URL in .env and that the service is up: "
                "docker compose up -d postgres",
            ),
            key="postgres",
        )


async def check_qdrant(settings: Settings, lang: Lang = "ru") -> CheckResult:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.qdrant_url}/healthz")
            resp.raise_for_status()
        return CheckResult(
            "Qdrant",
            True,
            _t(
                lang,
                f"подключено ({settings.qdrant_url})",
                f"connected ({settings.qdrant_url})",
            ),
            key="qdrant",
        )
    except Exception:
        return CheckResult(
            "Qdrant",
            False,
            _t(
                lang,
                f"недоступен на {settings.qdrant_url}",
                f"unreachable at {settings.qdrant_url}",
            ),
            _t(
                lang,
                "поднимите сервисы: docker compose up -d qdrant",
                "start the service: docker compose up -d qdrant",
            ),
            key="qdrant",
        )


async def check_llm_provider(settings: Settings, lang: Lang = "ru") -> CheckResult:
    name = _t(lang, "LLM-провайдер", "LLM provider")
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            return CheckResult(
                name,
                False,
                _t(
                    lang,
                    "OpenAI выбран, но OPENAI_API_KEY пуст",
                    "OpenAI selected, but OPENAI_API_KEY is empty",
                ),
                _t(
                    lang,
                    "укажите ключ в .env или переключитесь на Ollama: "
                    "LLM_PROVIDER=ollama, OLLAMA_HOST=http://localhost:11434",
                    "set the key in .env or switch to Ollama: "
                    "LLM_PROVIDER=ollama, OLLAMA_HOST=http://localhost:11434",
                ),
                key="llm",
            )
        return CheckResult(
            name,
            True,
            _t(
                lang,
                f"OpenAI, ключ задан (модель {settings.openai_model})",
                f"OpenAI, key set (model {settings.openai_model})",
            ),
            key="llm",
        )

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_host}/api/tags")
            resp.raise_for_status()
        return CheckResult(
            name,
            True,
            _t(
                lang,
                f"Ollama, сервер доступен (модель {settings.ollama_model})",
                f"Ollama, server reachable (model {settings.ollama_model})",
            ),
            key="llm",
        )
    except Exception:
        return CheckResult(
            name,
            False,
            _t(
                lang,
                f"Ollama выбран, но {settings.ollama_host} недоступен",
                f"Ollama selected, but {settings.ollama_host} is unreachable",
            ),
            _t(
                lang,
                "запустите ollama serve или укажите верный OLLAMA_HOST",
                "run ollama serve or set the correct OLLAMA_HOST",
            ),
            key="llm",
        )


def check_statements_dir(settings: Settings, lang: Lang = "ru") -> CheckResult:
    path = Path(settings.statements_dir)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    files = [p for p in path.rglob("*") if p.is_file()]
    return CheckResult(
        _t(lang, "Папка выписок", "Statements folder"),
        True,
        _t(
            lang,
            f"{path} (найдено {len(files)} файлов)",
            f"{path} ({len(files)} files found)",
        ),
        key="statements_dir",
    )


def check_mlflow(settings: Settings, lang: Lang = "ru") -> CheckResult:
    return CheckResult(
        _t(lang, "MLflow-трассировка", "MLflow tracing"),
        True,
        _t(
            lang,
            f"{settings.mlflow_tracking_uri} (эксперимент «{settings.mlflow_experiment_name}»)",
            f"{settings.mlflow_tracking_uri} (experiment “{settings.mlflow_experiment_name}”)",
        ),
        key="mlflow",
    )


def check_web_search(settings: Settings, lang: Lang = "ru") -> CheckResult:
    """Optional and informational only — the agent works fine without it, so this
    never counts as an environment "problem" the way a missing LLM key does."""
    name = _t(lang, "Веб-поиск", "Web search")
    if settings.tavily_api_key:
        return CheckResult(
            name, True, _t(lang, "Tavily, ключ задан", "Tavily, key set"), key="web_search"
        )
    return CheckResult(
        name,
        True,
        _t(lang, "отключён (TAVILY_API_KEY не задан)", "disabled (TAVILY_API_KEY not set)"),
        key="web_search",
    )


def check_tesseract(lang: Lang = "ru") -> CheckResult:
    binary = shutil.which("tesseract")
    if not binary:
        return CheckResult(
            "Tesseract OCR",
            False,
            _t(lang, "бинарь не найден в PATH", "binary not found in PATH"),
            _t(
                lang,
                "установите tesseract-ocr (+ языковые пакеты rus/eng) "
                "или используйте образ с ним",
                "install tesseract-ocr (+ rus/eng language packs) "
                "or use an image that includes it",
            ),
            key="tesseract",
        )
    try:
        output = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=3
        ).stdout.splitlines()
        version = output[0] if output else _t(lang, "неизвестна", "unknown")
        return CheckResult("Tesseract OCR", True, version, key="tesseract")
    except Exception:
        return CheckResult(
            "Tesseract OCR",
            True,
            _t(lang, "версия не определена", "version undetermined"),
            key="tesseract",
        )


async def run_health_checks(
    engine: AsyncEngine, settings: Settings, lang: Lang = "ru"
) -> list[CheckResult]:
    return [
        CheckResult(_t(lang, "Конфиг загружен", "Config loaded"), True, ".env", key="config"),
        await check_postgres(engine, settings, lang),
        await check_qdrant(settings, lang),
        await check_llm_provider(settings, lang),
        check_statements_dir(settings, lang),
        check_tesseract(lang),
        check_mlflow(settings, lang),
        check_web_search(settings, lang),
    ]
