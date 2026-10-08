import asyncio

import pytest
from qdrant_client import AsyncQdrantClient

from app.providers.qdrant_vector_store import QdrantVectorStore
from app.schemas.knowledge import KnowledgeChunk
from app.schemas.vector_store import VectorRecord


def record(chunk_id: str, vector: list[float], *, text: str | None = None) -> VectorRecord:
    return VectorRecord(
        vector=vector,
        chunk=KnowledgeChunk(
            chunk_id=chunk_id,
            doc_id="doc-1",
            title="Vehicle guide",
            section_title=f"Section {chunk_id}",
            source_url="https://example.com/guide",
            text=text or f"Evidence {chunk_id}",
        ),
    )


def test_qdrant_upsert_search_replace_and_delete_end_to_end() -> None:
    async def scenario() -> None:
        client = AsyncQdrantClient(":memory:")
        store = QdrantVectorStore(
            url="http://unused",
            collection_name="vehicle_knowledge_test",
            dimension=2,
            timeout_seconds=10,
            client=client,
        )
        try:
            await store.ensure_collection()
            await store.upsert(
                [
                    record("battery", [1.0, 0.0]),
                    record("fuel", [0.0, 1.0]),
                ]
            )

            first = await store.search([1.0, 0.0], k=2)
            assert [item.chunk_id for item in first] == ["battery", "fuel"]
            assert first[0].score == pytest.approx(1.0)

            await store.upsert([record("battery", [0.0, 1.0], text="Updated battery")])
            replaced = await store.search([0.0, 1.0], k=2)
            assert {item.chunk_id for item in replaced} == {"battery", "fuel"}
            battery = next(item for item in replaced if item.chunk_id == "battery")
            assert battery.text == "Updated battery"

            await store.delete(["battery", "unknown"])
            remaining = await store.search([1.0, 0.0], k=2)
            assert [item.chunk_id for item in remaining] == ["fuel"]
        finally:
            await client.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("vector", [[1.0], [0.0, 0.0], [float("nan"), 1.0]])
def test_upsert_rejects_invalid_vector(vector: list[float]) -> None:
    async def scenario() -> None:
        client = AsyncQdrantClient(":memory:")
        store = QdrantVectorStore(
            url="http://unused",
            collection_name="vehicle_knowledge_test",
            dimension=2,
            timeout_seconds=10,
            client=client,
        )
        try:
            await store.ensure_collection()
            with pytest.raises(ValueError, match="vector"):
                await store.upsert([record("bad", vector)])
        finally:
            await client.close()

    asyncio.run(scenario())


def test_delete_validates_whole_batch_before_deleting() -> None:
    async def scenario() -> None:
        client = AsyncQdrantClient(":memory:")
        store = QdrantVectorStore(
            url="http://unused",
            collection_name="vehicle_knowledge_test",
            dimension=2,
            timeout_seconds=10,
            client=client,
        )
        try:
            await store.ensure_collection()
            await store.upsert([record("battery", [1.0, 0.0])])
            with pytest.raises(ValueError, match="non-blank"):
                await store.delete(["battery", " "])
            assert [item.chunk_id for item in await store.search([1.0, 0.0], k=1)] == [
                "battery"
            ]
        finally:
            await client.close()

    asyncio.run(scenario())


def test_upsert_rejects_duplicate_ids_before_writing() -> None:
    async def scenario() -> None:
        client = AsyncQdrantClient(":memory:")
        store = QdrantVectorStore(
            url="http://unused",
            collection_name="vehicle_knowledge_test",
            dimension=2,
            timeout_seconds=10,
            client=client,
        )
        try:
            await store.ensure_collection()
            with pytest.raises(ValueError, match="duplicate"):
                await store.upsert(
                    [record("same", [1.0, 0.0]), record("same", [0.0, 1.0])]
                )
            assert await store.search([1.0, 0.0], k=1) == []
        finally:
            await client.close()

    asyncio.run(scenario())
