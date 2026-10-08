from app.schemas.retrieval import RetrievedSource


def reciprocal_rank_fusion(
    dense: list[RetrievedSource],
    lexical: list[RetrievedSource],
    *,
    k: int,
    rank_constant: int = 60,
) -> list[RetrievedSource]:
    """Fuse incomparable score scales using rank positions only."""
    if type(k) is not int or k <= 0 or type(rank_constant) is not int or rank_constant <= 0:
        raise ValueError("k and rank_constant must be positive integers")
    by_id: dict[str, RetrievedSource] = {}
    dense_scores = {item.chunk_id: item.score for item in dense}
    fusion_scores: dict[str, float] = {}
    for ranking in (dense, lexical):
        for rank, source in enumerate(ranking, start=1):
            by_id.setdefault(source.chunk_id, source)
            fusion_scores[source.chunk_id] = fusion_scores.get(source.chunk_id, 0.0) + 1 / (
                rank_constant + rank
            )

    ranked_ids = sorted(fusion_scores, key=lambda chunk_id: (-fusion_scores[chunk_id], chunk_id))
    results: list[RetrievedSource] = []
    for chunk_id in ranked_ids[:k]:
        source = by_id[chunk_id]
        # Keep cosine similarity in `score` for the existing evidence gate. A
        # lexical-only candidate receives 0 and cannot by itself bypass that gate.
        results.append(
            source.model_copy(
                update={
                    "score": dense_scores.get(chunk_id, 0.0),
                    "rank_score": fusion_scores[chunk_id],
                }
            )
        )
    return results
