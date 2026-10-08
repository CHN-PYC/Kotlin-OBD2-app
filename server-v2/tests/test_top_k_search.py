import pytest
from pydantic import ValidationError

from app.schemas.vector_search import IndexedVector
from app.services.retrieval.top_k_search import search_top_k


def candidate(chunk_id: str, vector: list[float]) -> IndexedVector:
    return IndexedVector(chunk_id=chunk_id, vector=vector)


def test_returns_highest_scores_in_descending_order_without_modifying_inputs() -> None:
    query = [1.0, 0.0]
    candidates = [
        candidate("opposite", [-1.0, 0.0]),
        candidate("partial", [3.0, 4.0]),
        candidate("same", [2.0, 0.0]),
    ]
    before = [item.model_dump() for item in candidates]

    hits = search_top_k(query, candidates, k=2)

    assert [hit.chunk_id for hit in hits] == ["same", "partial"]
    assert hits[0].score == pytest.approx(1.0)
    assert hits[1].score == pytest.approx(0.6)
    assert [item.model_dump() for item in candidates] == before
    assert query == [1.0, 0.0]


def test_equal_scores_keep_original_candidate_order() -> None:
    candidates = [candidate("first", [1.0, 1.0]), candidate("second", [2.0, 2.0])]
    assert [hit.chunk_id for hit in search_top_k([1.0, 1.0], candidates, k=2)] == [
        "first",
        "second",
    ]


def test_k_larger_than_candidates_returns_every_candidate() -> None:
    candidates = [candidate("a", [1.0, 0.0]), candidate("b", [0.0, 1.0])]
    assert len(search_top_k([1.0, 0.0], candidates, k=20)) == 2


def test_empty_candidates_return_empty_result() -> None:
    assert search_top_k([1.0, 0.0], [], k=5) == []


@pytest.mark.parametrize("k", [0, -1, 1.5, True])
def test_rejects_nonpositive_or_noninteger_k(k: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        search_top_k([1.0], [], k=k)  # type: ignore[arg-type]


def test_rejects_duplicate_chunk_ids() -> None:
    candidates = [candidate("same", [1.0, 0.0]), candidate("same", [0.0, 1.0])]
    with pytest.raises(ValueError, match="unique"):
        search_top_k([1.0, 0.0], candidates, k=1)


@pytest.mark.parametrize(
    "query,candidates",
    [
        ([], [candidate("a", [1.0])]),
        ([0.0, 0.0], [candidate("a", [1.0, 0.0])]),
        ([1.0], [candidate("a", [1.0, 0.0])]),
        ([float("nan")], [candidate("a", [1.0])]),
    ],
)
def test_rejects_invalid_query_or_dimension(
    query: list[float], candidates: list[IndexedVector]
) -> None:
    with pytest.raises(ValueError):
        search_top_k(query, candidates, k=1)


def test_indexed_vector_rejects_blank_id_and_invalid_vector() -> None:
    with pytest.raises(ValidationError):
        candidate(" ", [1.0])
    with pytest.raises(ValidationError):
        candidate("a", [])
