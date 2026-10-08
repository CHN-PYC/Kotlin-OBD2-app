from app.schemas.retrieval import RetrievedSource
from app.services.retrieval.fusion import reciprocal_rank_fusion


def source(chunk_id: str, score: float) -> RetrievedSource:
    return RetrievedSource(
        chunk_id=chunk_id,
        doc_id="doc",
        title="Guide",
        score=score,
        text=f"Evidence {chunk_id}",
    )


def test_rrf_rewards_candidates_found_by_both_retrievers() -> None:
    dense = [source("dense-only", 0.9), source("both", 0.8)]
    lexical = [source("both", 8.0), source("lexical-only", 7.0)]

    results = reciprocal_rank_fusion(dense, lexical, k=3)

    assert [item.chunk_id for item in results] == ["both", "dense-only", "lexical-only"]
    assert results[0].score == 0.8
    assert results[2].score == 0.0
    assert results[0].rank_score is not None
    assert results[0].rank_score > results[1].rank_score  # type: ignore[operator]


def test_rrf_rejects_invalid_k() -> None:
    try:
        reciprocal_rank_fusion([], [], k=0)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("invalid k must fail")
