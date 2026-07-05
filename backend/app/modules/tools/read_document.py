from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.modules.statements.service import StatementsService

MAX_CHARS = 8000


class ReadDocumentInput(BaseModel):
    path: str = Field(
        description="Путь к файлу в дереве документов, например '2025/апрель' или 'апрель'"
    )


def build_read_document_tool(statements_service: StatementsService) -> StructuredTool:
    """Fallback for when the structured pipeline can't help: an unrecognized PDF layout,
    a parse error, or a format the agent doesn't otherwise model. Returns raw text
    instead of leaving the agent stuck."""

    async def _run(path: str) -> str:
        try:
            text = await statements_service.read_raw_text(path)
        except Exception as exc:  # noqa: BLE001 - surfaced to the model, not a crash
            return f"Не удалось прочитать файл «{path}»: {exc}"

        if not text.strip():
            return f"Файл «{path}» прочитан, но не содержит текста."
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n…(текст обрезан)"
        return text

    return StructuredTool.from_function(
        coroutine=_run,
        name="read_document",
        description=(
            "Читает сырой текст файла выписки прямо с диска, без попытки разобрать "
            "транзакции. Используй, когда автоматический разбор не сработал (неизвестный "
            "формат банка, ошибка парсинга) или нужно свериться с исходным содержимым."
        ),
        args_schema=ReadDocumentInput,
    )
