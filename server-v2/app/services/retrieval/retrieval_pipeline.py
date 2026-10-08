from app.contracts.lexical_retriever import LexicalRetriever
from app.contracts.vector_store import VectorStore
from app.schemas.reranking import RerankedSource, RerankHit
from app.schemas.retrieval import RetrievedSource
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval.reranking import Reranker


class RetrievalPipeline:
    """Retrieve a broad candidate set, rerank all of it, then keep final K."""

    def __init__(
        self,
        vector_store: VectorStore,
        reranker: Reranker,
        lexical_retriever: LexicalRetriever | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._reranker = reranker
        self._lexical_retriever = lexical_retriever

    async def retrieve(
        self,
        query_text: str,
        query_vector: list[float],
        *,
        candidate_k: int,
        final_k: int,
    ) -> list[RerankedSource]:
        if not query_text.strip():
            raise ValueError("Query text must not be blank")
        if type(candidate_k) is not int or type(final_k) is not int:
            raise ValueError("candidate_k and final_k must be integers")
        if final_k <= 0 or candidate_k < final_k:
            raise ValueError("candidate_k must be greater than or equal to positive final_k")

        dense_candidates = await self._vector_store.search(query_vector, k=candidate_k)
        candidates = dense_candidates
        if self._lexical_retriever is not None:
            lexical_candidates = await self._lexical_retriever.search(query_text, k=candidate_k)
            candidates = reciprocal_rank_fusion(
                dense_candidates,
                lexical_candidates,
                k=candidate_k,
            )
        if not candidates:
            return []
        rerank_hits = await self._reranker.rerank(query_text, candidates)
        self._validate_rerank_hits(candidates, rerank_hits)
        # Scores are the contract; do not depend on a provider returning pre-sorted items.
        ranked_hits = sorted(rerank_hits, key=lambda hit: hit.score, reverse=True)
        source_by_id = {source.chunk_id: source for source in candidates}
        return [
            RerankedSource(
                source=source_by_id[hit.chunk_id].model_copy(deep=True),
                rerank_score=hit.score,
                rerank_provider=hit.rerank_provider,
            )
            for hit in ranked_hits[:final_k]
        ]

    @staticmethod
    def _validate_rerank_hits(candidates: list[RetrievedSource], hits: list[RerankHit]) -> None:
        candidate_ids = [item.chunk_id for item in candidates]
        hit_ids = [item.chunk_id for item in hits]
        if len(hit_ids) != len(set(hit_ids)):
            raise ValueError("Reranker returned duplicate chunk IDs")
        if set(hit_ids) != set(candidate_ids) or len(hit_ids) != len(candidate_ids):
            raise ValueError("Reranker must return every candidate exactly once")
