import asyncio

import pytest

from app.schemas.knowledge import KnowledgeChunk
from app.schemas.vector_store import VectorRecord
from app.services.retrieval.memory_vector_store import MemoryVectorStore


def record(chunk_id: str, vector: list[float]) -> VectorRecord:
    return VectorRecord(
        vector=vector,
        chunk=KnowledgeChunk(
            chunk_id=chunk_id,
            doc_id="doc-1",
            title="Guide",
            section_title=f"Section {chunk_id}",
            source_url="https://example.com",
            text=f"Evidence {chunk_id}",
        ),
    )


def populated_store() -> MemoryVectorStore:
    store = MemoryVectorStore(dimension=2)
    asyncio.run(
        store.upsert(
            [
                record("a", [1.0, 0.0]),
                record("b", [3.0, 4.0]),
                record("c", [-1.0, 0.0]),
            ]
        )
    )
    return store


def test_search_returns_ranked_sources_with_text() -> None:
    results = asyncio.run(populated_store().search([1.0, 0.0], k=2))

    assert [result.chunk_id for result in results] == ["a", "b"]
    assert [result.text for result in results] == ["Evidence a", "Evidence b"]
    assert results[0].score == pytest.approx(1.0)
    assert results[1].score == pytest.approx(0.6)


def test_search_result_mutation_does_not_change_stored_chunk() -> None:
    store = populated_store()
    first = asyncio.run(store.search([1.0, 0.0], k=1))
    first[0].text = "changed outside"

    second = asyncio.run(store.search([1.0, 0.0], k=1))
    assert second[0].text == "Evidence a"


def test_delete_removes_existing_ids_and_ignores_unknown_ids() -> None:
    store = populated_store()
    asyncio.run(store.delete(["a", "unknown"]))

    results = asyncio.run(store.search([1.0, 0.0], k=3))
    assert [result.chunk_id for result in results] == ["b", "c"]


def test_delete_rejects_invalid_batch_before_removing_anything() -> None:
    store = populated_store()
    with pytest.raises(ValueError, match="non-blank"):
        asyncio.run(store.delete(["a", " "]))

    results = asyncio.run(store.search([1.0, 0.0], k=3))
    assert [result.chunk_id for result in results] == ["a", "b", "c"]


@pytest.mark.parametrize("k", [0, -1, True])
def test_search_rejects_invalid_k(k: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        asyncio.run(populated_store().search([1.0, 0.0], k=k))  # type: ignore[arg-type]
