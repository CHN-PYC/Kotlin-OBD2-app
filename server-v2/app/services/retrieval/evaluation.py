from app.schemas.evaluation import RetrievalEvalCase, RetrievalMetrics


def evaluate_rankings(
    cases: list[RetrievalEvalCase],
    rankings: dict[str, list[str]],
    *,
    k: int,
) -> RetrievalMetrics:
    if not cases:
        raise ValueError("cases must not be empty")
    if type(k) is not int or k <= 0:
        raise ValueError("k must be a positive integer")
    if set(rankings) != {case.case_id for case in cases}:
        raise ValueError("rankings must contain every case exactly once")

    hits = recalls = precisions = reciprocal_ranks = 0.0
    for case in cases:
        ranked = rankings[case.case_id][:k]
        if len(ranked) != len(set(ranked)):
            raise ValueError(f"ranking contains duplicate chunk IDs: {case.case_id}")
        relevant_positions = [
            index
            for index, chunk_id in enumerate(ranked, start=1)
            if chunk_id in case.relevant_chunk_ids
        ]
        relevant_count = len(relevant_positions)
        hits += float(relevant_count > 0)
        recalls += relevant_count / len(case.relevant_chunk_ids)
        # Precision uses requested K as denominator so short result sets do not look
        # artificially perfect when a retriever returns fewer candidates than asked.
        precisions += relevant_count / k
        reciprocal_ranks += 1 / relevant_positions[0] if relevant_positions else 0.0

    count = len(cases)
    return RetrievalMetrics(
        case_count=count,
        k=k,
        hit_at_k=hits / count,
        recall_at_k=recalls / count,
        precision_at_k=precisions / count,
        mrr=reciprocal_ranks / count,
    )
