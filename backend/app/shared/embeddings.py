from llama_index.core.base.embeddings.base import BaseEmbedding

from app.core.config import Settings


def get_embedding_model(settings: Settings) -> BaseEmbedding:
    """Same provider switch as shared/llm.py, but for the embeddings side of RAG."""
    if settings.llm_provider == "openai":
        from llama_index.embeddings.openai import OpenAIEmbedding

        return OpenAIEmbedding(model="text-embedding-3-small", api_key=settings.openai_api_key)

    from llama_index.embeddings.ollama import OllamaEmbedding

    return OllamaEmbedding(model_name="nomic-embed-text", base_url=settings.ollama_host)
