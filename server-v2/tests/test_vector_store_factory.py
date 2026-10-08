import asyncio

from qdrant_client import AsyncQdrantClient

from app.core.config import Settings, VectorStoreProvider
from app.providers.factory import create_vector_store
from app.providers.qdrant_vector_store import QdrantVectorStore
from app.services.retrieval.memory_vector_store import MemoryVectorStore


def test_factory_creates_memory_store_without_external_service() -> None:
    settings = Settings(
        _env_file=None,
        vector_store_provider=VectorStoreProvider.MEMORY,
        embedding_dimension=2,
    )
    store = asyncio.run(create_vector_store(settings))
    assert isinstance(store, MemoryVectorStore)


def test_factory_creates_and_initializes_qdrant_store() -> None:
    async def scenario() -> None:
        client = AsyncQdrantClient(":memory:")
        settings = Settings(
            _env_file=None,
            vector_store_provider=VectorStoreProvider.QDRANT,
            embedding_dimension=2,
            qdrant_collection_name="factory_test",
        )
        try:
            store = await create_vector_store(settings, client=client)
            assert isinstance(store, QdrantVectorStore)
            assert await client.collection_exists("factory_test")
        finally:
            await client.close()

    asyncio.run(scenario())
