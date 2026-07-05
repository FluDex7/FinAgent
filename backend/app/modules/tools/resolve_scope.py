import json
import re
from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel

from app.modules.statements.schemas import DocFolderOut

SCOPE_PROMPT_TEMPLATE = """Ты помогаешь агенту FinAgent определить, к каким выпискам относится \
вопрос пользователя.

Дерево документов (папка: файлы):
{tree}

Вопрос пользователя: {question}

Верни ТОЛЬКО JSON без пояснений и markdown, в одном из двух видов:
1) {{"files": ["2025/Q1", "2025"], "explanation": "короткое объяснение выбора"}}
   - "2025" (без слэша) означает всю папку/год целиком.
   - "2025/Q1" означает конкретный файл в папке.
2) {{"clarification": "уточняющий вопрос пользователю"}} — используй, только если однозначно
   определить область невозможно (например, подходит несколько кандидатов)."""

_CODE_FENCE_RE = re.compile(r"^```(?:json)?|```$", re.IGNORECASE | re.MULTILINE)


def describe_tree(folders: list[DocFolderOut]) -> str:
    lines = []
    for folder in folders:
        name = folder.name or "(без папки)"
        files = ", ".join(f.name for f in folder.files) or "—"
        lines.append(f"- {name}: {files}")
    return "\n".join(lines)


@dataclass
class ScopeResolution:
    files: list[str]
    explanation: str
    clarification: str | None = None

    @property
    def needs_clarification(self) -> bool:
        return self.clarification is not None


def _strip_code_fence(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text).strip()


_FALLBACK_CLARIFICATION = "Уточните, пожалуйста, за какой период вас интересуют траты?"


async def resolve_scope(
    chat_model: BaseChatModel, question: str, folders: list[DocFolderOut]
) -> ScopeResolution:
    prompt = SCOPE_PROMPT_TEMPLATE.format(tree=describe_tree(folders), question=question)
    response = await chat_model.ainvoke(prompt)
    content = response.content if isinstance(response.content, str) else str(response.content)
    raw = _strip_code_fence(content)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return ScopeResolution(files=[], explanation="", clarification=_FALLBACK_CLARIFICATION)

    if parsed.get("clarification"):
        return ScopeResolution(files=[], explanation="", clarification=parsed["clarification"])

    return ScopeResolution(files=parsed.get("files", []), explanation=parsed.get("explanation", ""))
