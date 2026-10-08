import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from qdrant_client.models import Distance, VectorParams

from app.providers.qdrant_vector_store import QdrantVectorStore


class FakeQdrantClient:
    def __init__(self, *, exists: bool, vectors: Any = None) -> None:
        self.exists = exists
        self.vectors = vectors
        self.created_name: str | None = None
        self.created_vectors: VectorParams | None = None

    async def collection_exists(self, collection_name: str) -> bool:
        return self.exists

    async def create_collection(
        self,
        collection_name: str,
        vectors_config: VectorParams,
    ) -> bool:
        self.created_name = collection_name
        self.created_vectors = vectors_config
        return True

    async def get_collection(self, collection_name: str) -> Any:
        return SimpleNamespace(
            config=SimpleNamespace(params=SimpleNamespace(vectors=self.vectors))
        )


def store(client: FakeQdrantClient, *, dimension: int = 1024) -> QdrantVectorStore:
    return QdrantVectorStore(
        url="http://localhost:6333",
        collection_name="vehicle_knowledge_v1",
        dimension=dimension,
        timeout_seconds=10,
        client=client,  # type: ignore[arg-type]
    )


def test_creates_missing_collection_with_cosine_distance() -> None:
    client = FakeQdrantClient(exists=False)
    asyncio.run(store(client).ensure_collection())

    assert client.created_name == "vehicle_knowledge_v1"
    assert client.created_vectors is not None
    assert client.created_vectors.size == 1024
    assert client.created_vectors.distance is Distance.COSINE


def test_accepts_existing_matching_collection_without_recreating_it() -> None:
    client = FakeQdrantClient(
        exists=True,
        vectors=VectorParams(size=1024, distance=Distance.COSINE),
    )
    asyncio.run(store(client).ensure_collection())
    assert client.created_name is None


@pytest.mark.parametrize(
    "vectors",
    [
        VectorParams(size=768, distance=Distance.COSINE),
        VectorParams(size=1024, distance=Distance.DOT),
        {"dense": VectorParams(size=1024, distance=Distance.COSINE)},
    ],
)
def test_rejects_incompatible_existing_collection(vectors: Any) -> None:
    client = FakeQdrantClient(exists=True, vectors=vectors)
    with pytest.raises(ValueError, match="collection"):
        asyncio.run(store(client).ensure_collection())
