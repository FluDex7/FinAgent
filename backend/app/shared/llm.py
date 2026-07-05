from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import Settings


def get_chat_model(settings: Settings) -> BaseChatModel:
    """Returns the configured chat model — callers never branch on provider themselves."""
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model, api_key=settings.openai_api_key, temperature=0
        )

    from langchain_ollama import ChatOllama

    return ChatOllama(model=settings.ollama_model, base_url=settings.ollama_host, temperature=0)
