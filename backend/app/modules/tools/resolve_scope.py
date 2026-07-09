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
2) {{"clarification": "<твой уточняющий вопрос пользователю, а не этот текст>"}} — используй,
   только если однозначно определить область невозможно (например, подходит несколько
   кандидатов) И вопрос вообще касается данных пользователя. Пиши clarification на том же
   языке, на котором задан вопрос пользователя. Для приветствий, благодарностей
   и вопросов не про финансы верни вариант 1 с пустым files: {{"files": [], "explanation": ""}}."""

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


_FALLBACK_CLARIFICATION_RU = "Уточните, пожалуйста, за какой период вас интересуют траты?"
_FALLBACK_CLARIFICATION_EN = "Could you clarify which period you're asking about?"


def _fallback_clarification(question: str) -> str:
    # The fallback is shown to the user verbatim, so it should at least match
    # their language — Cyrillic in the question is a good-enough signal.
    return (
        _FALLBACK_CLARIFICATION_RU
        if re.search(r"[а-яё]", question, re.IGNORECASE)
        else _FALLBACK_CLARIFICATION_EN
    )

# Models occasionally echo the prompt's own placeholder text back as if it were
# a real answer instead of substituting their own question — catch that here
# rather than showing the user a literal instruction fragment.
_PLACEHOLDER_MARKERS = ("твой уточняющий вопрос", "уточняющий вопрос пользователю")


def _looks_like_placeholder(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


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
        return ScopeResolution(
            files=[], explanation="", clarification=_fallback_clarification(question)
        )

    clarification = parsed.get("clarification")
    if clarification:
        if _looks_like_placeholder(clarification):
            clarification = _fallback_clarification(question)
        return ScopeResolution(files=[], explanation="", clarification=clarification)

    return ScopeResolution(files=parsed.get("files", []), explanation=parsed.get("explanation", ""))
