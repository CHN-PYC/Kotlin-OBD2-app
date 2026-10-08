import asyncio

import pytest

from app.schemas.knowledge import KnowledgeChunk
from app.schemas.vector_store import VectorRecord
from app.services.retrieval.memory_vector_store import MemoryVectorStore


def record(chunk_id: str, vector: list[float], *, text: str = "evidence") -> VectorRecord:
    return VectorRecord(
        vector=vector,
        chunk=KnowledgeChunk(
            chunk_id=chunk_id,
            doc_id="doc-1",
            title="Guide",
            section_title="Checks",
            source_url="https://example.com",
            text=text,
        ),
    )


def test_upsert_adds_and_replaces_records_by_chunk_id() -> None:
    store = MemoryVectorStore(dimension=2)

    asyncio.run(store.upsert([record("a", [1.0, 0.0], text="old")]))
    asyncio.run(store.upsert([record("a", [0.0, 1.0], text="new")]))

    assert len(store._records) == 1
    assert store._records["a"].vector == [0.0, 1.0]
    assert store._records["a"].chunk.text == "new"


def test_upsert_keeps_an_independent_copy() -> None:
    store = MemoryVectorStore(dimension=2)
    original = record("a", [1.0, 0.0])
    asyncio.run(store.upsert([original]))

    original.vector[0] = 99.0
    original.chunk.text = "changed outside"

    assert store._records["a"].vector == [1.0, 0.0]
    assert store._records["a"].chunk.text == "evidence"


@pytest.mark.parametrize("bad_vector", [[1.0], [0.0, 0.0]])
def test_invalid_record_rejects_the_whole_batch(bad_vector: list[float]) -> None:
    store = MemoryVectorStore(dimension=2)

    with pytest.raises(ValueError):
        asyncio.run(store.upsert([record("valid", [1.0, 0.0]), record("bad", bad_vector)]))

    assert store._records == {}


def test_rejects_duplicate_ids_in_one_batch() -> None:
    store = MemoryVectorStore(dimension=2)
    with pytest.raises(ValueError, match="duplicate"):
        asyncio.run(store.upsert([record("a", [1.0, 0.0]), record("a", [0.0, 1.0])]))
    assert store._records == {}
