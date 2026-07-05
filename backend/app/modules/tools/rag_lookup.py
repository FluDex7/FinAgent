from pathlib import Path

from langchain_core.tools import StructuredTool
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

from app.core.config import Settings
from app.shared.embeddings import get_embedding_model

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
COLLECTION_NAME = "finagent_knowledge"
DEFAULT_TOP_K = 3


class RagLookupInput(BaseModel):
    query: str = Field(
        description="Справочный вопрос о самом FinAgent: категоризация, форматы, возможности"
    )


def get_or_build_index(
    settings: Settings, qdrant_client: QdrantClient, *, collection_name: str = COLLECTION_NAME
) -> VectorStoreIndex:
    """Embeds the local knowledge base into Qdrant once; later calls just attach to it —
    a real Qdrant server (docker-compose) persists the collection across process restarts."""
    vector_store = QdrantVectorStore(client=qdrant_client, collection_name=collection_name)
    embed_model = get_embedding_model(settings)

    if qdrant_client.collection_exists(collection_name):
        return VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)

    documents = SimpleDirectoryReader(str(KNOWLEDGE_DIR)).load_data()
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_documents(
        documents, storage_context=storage_context, embed_model=embed_model
    )


async def rag_lookup(
    settings: Settings,
    query: str,
    *,
    qdrant_client: QdrantClient | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> str:
    """Retrieval only — no answer synthesis. The agent's own chat model reads this
    context and writes the actual reply, matching the "rag_lookup → context" contract."""
    try:
        client = qdrant_client or QdrantClient(url=settings.qdrant_url)
        index = get_or_build_index(settings, client)
        retriever = index.as_retriever(similarity_top_k=top_k)
        # .retrieve (sync) — QdrantVectorStore's async path needs a separate AsyncQdrantClient,
        # not worth the extra wiring for a fast local vector search.
        nodes = retriever.retrieve(query)
    except Exception as exc:  # noqa: BLE001 - Qdrant/embeddings down must not break the chat
        return f"Справочник временно недоступен: {exc}"

    if not nodes:
        return "В справочнике FinAgent не нашлось ответа на этот вопрос."
    return "\n\n---\n\n".join(node.get_content() for node in nodes)


def build_rag_lookup_tool(
    settings: Settings, *, qdrant_client: QdrantClient | None = None
) -> StructuredTool:
    async def _run(query: str) -> str:
        return await rag_lookup(settings, query, qdrant_client=qdrant_client)

    return StructuredTool.from_function(
        coroutine=_run,
        name="rag_lookup",
        description=(
            "Ищет справочную информацию о самом FinAgent: как он категоризирует траты, какие "
            "форматы выписок понимает, что вообще умеет. Не для вопросов о конкретных суммах — "
            "для этого используй sql_query."
        ),
        args_schema=RagLookupInput,
    )
