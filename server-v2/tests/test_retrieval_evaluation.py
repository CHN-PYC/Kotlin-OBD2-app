import pytest

from app.schemas.evaluation import RetrievalEvalCase
from app.services.retrieval.evaluation import evaluate_rankings


def case(case_id: str, relevant: set[str]) -> RetrievalEvalCase:
    return RetrievalEvalCase(case_id=case_id, query="query", relevant_chunk_ids=relevant)


def test_computes_hit_recall_precision_and_mrr() -> None:
    cases = [case("one", {"a", "b"}), case("two", {"c"})]
    metrics = evaluate_rankings(
        cases,
        {"one": ["x", "a"], "two": ["c", "z"]},
        k=2,
    )

    assert metrics.hit_at_k == 1.0
    assert metrics.recall_at_k == 0.75
    assert metrics.precision_at_k == 0.5
    assert metrics.mrr == 0.75


def test_zero_when_no_relevant_chunk_is_retrieved() -> None:
    metrics = evaluate_rankings([case("one", {"a"})], {"one": ["x"]}, k=2)

    assert metrics.hit_at_k == metrics.recall_at_k == 0
    assert metrics.precision_at_k == metrics.mrr == 0


@pytest.mark.parametrize(
    "rankings,k",
    [({}, 2), ({"one": ["a", "a"]}, 2), ({"one": ["a"]}, 0)],
)
def test_rejects_incomplete_duplicate_or_invalid_inputs(
    rankings: dict[str, list[str]], k: int
) -> None:
    with pytest.raises(ValueError):
        evaluate_rankings([case("one", {"a"})], rankings, k=k)
