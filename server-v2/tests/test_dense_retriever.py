import pytest

from app.schemas.knowledge import KnowledgeChunk
from app.schemas.vector_search import IndexedVector
from app.services.retrieval.dense_retriever import ExactDenseRetriever


def chunk(chunk_id: str) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=chunk_id,
        doc_id="doc-1",
        title="Sensor guide",
        section_title=f"Section {chunk_id}",
        source_url="https://example.com/guide",
        text=f"Evidence {chunk_id}",
    )


def vector(chunk_id: str, values: list[float]) -> IndexedVector:
    return IndexedVector(chunk_id=chunk_id, vector=values)


def test_retrieves_ranked_sources_end_to_end() -> None:
    retriever = ExactDenseRetriever(
        [vector("a", [1.0, 0.0]), vector("b", [3.0, 4.0]), vector("c", [-1.0, 0.0])],
        [chunk("c"), chunk("a"), chunk("b")],
    )
    sources = retriever.retrieve([1.0, 0.0], k=2)
    assert [source.chunk_id for source in sources] == ["a", "b"]
    assert [source.text for source in sources] == ["Evidence a", "Evidence b"]
    assert sources[0].score == pytest.approx(1.0)
    assert sources[1].score == pytest.approx(0.6)


def test_keeps_an_independent_snapshot_of_vectors_and_chunks() -> None:
    vectors = [vector("a", [1.0, 0.0])]
    chunks = [chunk("a")]
    retriever = ExactDenseRetriever(vectors, chunks)
    vectors[0].vector[:] = [-1.0, 0.0]
    chunks[0].text = "Changed outside"
    vectors.clear()
    chunks.clear()
    source = retriever.retrieve([1.0, 0.0], k=1)[0]
    assert source.score == pytest.approx(1.0)
    assert source.text == "Evidence a"


def test_empty_consistent_index_returns_empty_results() -> None:
    assert ExactDenseRetriever([], []).retrieve([1.0], k=5) == []


@pytest.mark.parametrize(
    "vectors,chunks",
    [
        ([vector("a", [1.0])], []),
        ([], [chunk("a")]),
        ([vector("a", [1.0])], [chunk("b")]),
        ([vector("a", [1.0]), vector("a", [2.0])], [chunk("a")]),
        ([vector("a", [1.0])], [chunk("a"), chunk("a")]),
    ],
)
def test_rejects_inconsistent_or_duplicate_ids(
    vectors: list[IndexedVector], chunks: list[KnowledgeChunk]
) -> None:
    with pytest.raises(ValueError):
        ExactDenseRetriever(vectors, chunks)


def test_rejects_inconsistent_dimensions_before_any_query() -> None:
    with pytest.raises(ValueError, match="same dimension"):
        ExactDenseRetriever(
            [vector("a", [1.0]), vector("b", [1.0, 0.0])],
            [chunk("a"), chunk("b")],
        )


def test_rejects_zero_vector_before_any_query() -> None:
    with pytest.raises(ValueError, match="all zero"):
        ExactDenseRetriever([vector("a", [0.0, -0.0])], [chunk("a")])


@pytest.mark.parametrize("k", [0, -1])
def test_retrieve_preserves_top_k_validation(k: int) -> None:
    retriever = ExactDenseRetriever([], [])
    with pytest.raises(ValueError, match="positive integer"):
        retriever.retrieve([1.0], k=k)


def test_retrieve_propagates_invalid_query_dimension() -> None:
    retriever = ExactDenseRetriever([vector("a", [1.0, 0.0])], [chunk("a")])
    with pytest.raises(ValueError, match="same dimension"):
        retriever.retrieve([1.0], k=1)
