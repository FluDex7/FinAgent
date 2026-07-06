from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.modules.statements.models import StatementStatus
from app.modules.statements.schemas import DocFileOut, DocFolderOut
from app.modules.tools.resolve_scope import describe_tree, resolve_scope

TREE = [
    DocFolderOut(
        name="2024",
        files=[
            DocFileOut(
                id="s1", name="Q1", folder="2024", tx_count=10,
                date_from=None, date_to=None, status=StatementStatus.parsed,
            ),
        ],
    ),
    DocFolderOut(
        name="2025",
        files=[
            DocFileOut(
                id="s2", name="Q1", folder="2025", tx_count=20,
                date_from=None, date_to=None, status=StatementStatus.parsed,
            ),
            DocFileOut(
                id="2025/апрель", name="апрель", folder="2025", tx_count=0,
                date_from=None, date_to=None, status=StatementStatus.new,
            ),
        ],
    ),
]


def test_describe_tree_lists_folders_and_files():
    description = describe_tree(TREE)
    assert "2024: Q1" in description
    assert "2025: Q1, апрель" in description


async def test_resolve_scope_parses_files_json():
    model = FakeListChatModel(
        responses=['{"files": ["2025/Q1"], "explanation": "нашёл Q1 2025"}']
    )
    result = await resolve_scope(model, "траты за первый квартал 2025", TREE)
    assert result.files == ["2025/Q1"]
    assert result.explanation == "нашёл Q1 2025"
    assert not result.needs_clarification


async def test_resolve_scope_strips_code_fence():
    model = FakeListChatModel(
        responses=['```json\n{"files": ["2024"], "explanation": "весь 2024 год"}\n```']
    )
    result = await resolve_scope(model, "траты за 24 год", TREE)
    assert result.files == ["2024"]


async def test_resolve_scope_returns_clarification_when_ambiguous():
    model = FakeListChatModel(
        responses=['{"clarification": "Уточните, апрель какого года вас интересует?"}']
    )
    result = await resolve_scope(model, "в апреле", TREE)
    assert result.needs_clarification
    assert "апрель" in result.clarification


async def test_resolve_scope_falls_back_to_clarification_on_bad_json():
    model = FakeListChatModel(responses=["это не json вовсе"])
    result = await resolve_scope(model, "что-то", TREE)
    assert result.needs_clarification


async def test_resolve_scope_replaces_echoed_placeholder_text():
    # A model can echo the prompt's own placeholder instead of writing a real
    # question — this must never reach the user verbatim.
    model = FakeListChatModel(
        responses=['{"clarification": "твой уточняющий вопрос пользователю, а не этот текст"}']
    )
    result = await resolve_scope(model, "привет", TREE)
    assert result.needs_clarification
    assert result.clarification == "Уточните, пожалуйста, за какой период вас интересуют траты?"
