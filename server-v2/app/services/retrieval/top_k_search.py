from app.schemas.vector_search import IndexedVector, VectorSearchHit
from app.services.retrieval.vector_similarity import cosine_similarity


def search_top_k(
    query_vector: list[float],
    candidates: list[IndexedVector],
    *,
    k: int,
) -> list[VectorSearchHit]:
    """Score all candidates by cosine similarity and return the best K."""
    if type(k) is not int or k <= 0:
        raise ValueError("k must be a positive integer")
    if not candidates:
        return []

    chunk_ids = [candidate.chunk_id for candidate in candidates]
    if len(set(chunk_ids)) != len(chunk_ids):
        raise ValueError("Candidate chunk IDs must be unique")

    hits = [
        VectorSearchHit(
            chunk_id=candidate.chunk_id,
            score=cosine_similarity(query_vector, candidate.vector),
        )
        for candidate in candidates
    ]
    # Python's sort is stable, so equal scores retain their candidate input order.
    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits[:k]
