from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.shared.llm import get_chat_model


def test_openai_provider_returns_chat_openai():
    settings = Settings(llm_provider="openai", openai_api_key="sk-test", openai_model="gpt-4o-mini")
    model = get_chat_model(settings)
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "gpt-4o-mini"


def test_ollama_provider_returns_chat_ollama():
    settings = Settings(
        llm_provider="ollama", ollama_host="http://localhost:11434", ollama_model="mistral"
    )
    model = get_chat_model(settings)
    assert isinstance(model, ChatOllama)
    assert model.model == "mistral"
