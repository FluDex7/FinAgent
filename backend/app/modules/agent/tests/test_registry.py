from unittest.mock import MagicMock

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.core.config import Settings
from app.modules.agent.registry import build_tools


def _build(tavily_api_key: str | None) -> list[str]:
    settings = Settings(tavily_api_key=tavily_api_key)
    tools = build_tools(MagicMock(), MagicMock(), FakeListChatModel(responses=[]), settings)
    return [t.name for t in tools]


def test_web_search_absent_without_tavily_key():
    names = _build(None)
    assert "web_search" not in names


def test_web_search_present_with_tavily_key():
    names = _build("tvly-test-key")
    assert "web_search" in names
