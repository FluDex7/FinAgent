import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    hint: str | None = None


async def check_postgres(engine: AsyncEngine, settings: Settings) -> CheckResult:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return CheckResult("PostgreSQL", True, "подключено")
    except Exception as exc:
        return CheckResult(
            "PostgreSQL",
            False,
            f"недоступен ({exc.__class__.__name__})",
            "проверьте DATABASE_URL в .env и что сервис поднят: docker compose up -d postgres",
        )


async def check_qdrant(settings: Settings) -> CheckResult:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.qdrant_url}/healthz")
            resp.raise_for_status()
        return CheckResult("Qdrant", True, f"подключено ({settings.qdrant_url})")
    except Exception:
        return CheckResult(
            "Qdrant",
            False,
            f"недоступен на {settings.qdrant_url}",
            "поднимите сервисы: docker compose up -d qdrant",
        )


async def check_llm_provider(settings: Settings) -> CheckResult:
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            return CheckResult(
                "LLM-провайдер",
                False,
                "OpenAI выбран, но OPENAI_API_KEY пуст",
                "укажите ключ в .env или переключитесь на Ollama: "
                "LLM_PROVIDER=ollama, OLLAMA_HOST=http://localhost:11434",
            )
        return CheckResult(
            "LLM-провайдер", True, f"OpenAI, ключ задан (модель {settings.openai_model})"
        )

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_host}/api/tags")
            resp.raise_for_status()
        return CheckResult(
            "LLM-провайдер", True, f"Ollama, сервер доступен (модель {settings.ollama_model})"
        )
    except Exception:
        return CheckResult(
            "LLM-провайдер",
            False,
            f"Ollama выбран, но {settings.ollama_host} недоступен",
            "запустите ollama serve или укажите верный OLLAMA_HOST",
        )


def check_statements_dir(settings: Settings) -> CheckResult:
    path = Path(settings.statements_dir)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    files = [p for p in path.rglob("*") if p.is_file()]
    return CheckResult("Папка выписок", True, f"{path} (найдено {len(files)} файлов)")


def check_tesseract() -> CheckResult:
    binary = shutil.which("tesseract")
    if not binary:
        return CheckResult(
            "Tesseract OCR",
            False,
            "бинарь не найден в PATH",
            "установите tesseract-ocr (+ языковые пакеты rus/eng) или используйте образ с ним",
        )
    try:
        output = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=3
        ).stdout.splitlines()
        version = output[0] if output else "неизвестна"
        return CheckResult("Tesseract OCR", True, version)
    except Exception:
        return CheckResult("Tesseract OCR", True, "версия не определена")


async def run_health_checks(engine: AsyncEngine, settings: Settings) -> list[CheckResult]:
    return [
        CheckResult("Конфиг загружен", True, ".env"),
        await check_postgres(engine, settings),
        await check_qdrant(settings),
        await check_llm_provider(settings),
        check_statements_dir(settings),
        check_tesseract(),
    ]
