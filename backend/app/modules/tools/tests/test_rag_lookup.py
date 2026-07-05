from unittest.mock import patch

import pytest
from llama_index.core.embeddings import MockEmbedding
from qdrant_client import QdrantClient

from app.core.config import Settings
from app.modules.tools.rag_lookup import (
    COLLECTION_NAME,
    build_rag_lookup_tool,
    get_or_build_index,
    rag_lookup,
)


@pytest.fixture
def mock_embedding():
    with patch(
        "app.modules.tools.rag_lookup.get_embedding_model",
        return_value=MockEmbedding(embed_dim=8),
    ):
        yield


@pytest.fixture
def qdrant_client():
    return QdrantClient(location=":memory:")


def test_get_or_build_index_creates_collection(mock_embedding, qdrant_client):
    assert not qdrant_client.collection_exists(COLLECTION_NAME)

    get_or_build_index(Settings(), qdrant_client)

    assert qdrant_client.collection_exists(COLLECTION_NAME)
    count = qdrant_client.count(COLLECTION_NAME).count
    assert count > 0


def test_get_or_build_index_reuses_existing_collection(mock_embedding, qdrant_client):
    get_or_build_index(Settings(), qdrant_client)
    first_count = qdrant_client.count(COLLECTION_NAME).count

    with patch(
        "app.modules.tools.rag_lookup.SimpleDirectoryReader"
    ) as reader_cls:
        get_or_build_index(Settings(), qdrant_client)
        reader_cls.assert_not_called()

    assert qdrant_client.count(COLLECTION_NAME).count == first_count


async def test_rag_lookup_returns_knowledge_base_content(mock_embedding, qdrant_client):
    result = await rag_lookup(
        Settings(), "Как категоризируются траты?", qdrant_client=qdrant_client
    )

    assert "Справочник временно недоступен" not in result
    assert len(result) > 0


async def test_rag_lookup_handles_qdrant_failure_gracefully():
    unreachable = QdrantClient(url="http://localhost:1")

    result = await rag_lookup(Settings(), "что угодно", qdrant_client=unreachable)

    assert "Справочник временно недоступен" in result


async def test_build_rag_lookup_tool_end_to_end(mock_embedding, qdrant_client):
    tool = build_rag_lookup_tool(Settings(), qdrant_client=qdrant_client)
    result = await tool.ainvoke({"query": "Что умеет FinAgent?"})

    assert isinstance(result, str)
    assert len(result) > 0
