import logging
from typing import Protocol

from app.providers.errors import ModelProviderError
from app.providers.reranking import CrossEncoderModel
from app.schemas.reranking import RerankHit, RerankPair
from app.schemas.retrieval import RetrievedSource


class Reranker(Protocol):
    async def rerank(
        self,
        query_text: str,
        candidates: list[RetrievedSource],
    ) -> list[RerankHit]: ...


class PassThroughReranker:
    """A no-model baseline that preserves dense order and score."""

    async def rerank(
        self,
        query_text: str,
        candidates: list[RetrievedSource],
    ) -> list[RerankHit]:
        if not query_text.strip():
            raise ValueError("Query text must not be blank")
        return [
            RerankHit(
                chunk_id=item.chunk_id,
                score=item.rank_score if item.rank_score is not None else item.score,
                rerank_provider="pass_through",
            )
            for item in candidates
        ]


class CrossEncoderReranker:
    """Adapt a pair-scoring model to the retrieval pipeline's ID-based contract."""

    def __init__(self, model: CrossEncoderModel) -> None:
        self._model = model

    async def rerank(
        self,
        query_text: str,
        candidates: list[RetrievedSource],
    ) -> list[RerankHit]:
        if not query_text.strip():
            raise ValueError("Query text must not be blank")
        if not candidates:
            return []

        pairs = [RerankPair(query_text=query_text, document_text=item.text) for item in candidates]
        result = await self._model.score_pairs(pairs)
        if len(result.scores) != len(candidates):
            raise ValueError("Cross-Encoder must return one score per candidate")

        return [
            RerankHit(
                chunk_id=item.chunk_id,
                score=score,
                rerank_provider=f"{result.provider}:{result.model}",
            )
            for item, score in zip(candidates, result.scores, strict=True)
        ]


class ResilientReranker:
    """Use dense order when the optional model provider fails at runtime."""

    def __init__(self, primary: Reranker, fallback: Reranker) -> None:
        self._primary = primary
        self._fallback = fallback
        self._logger = logging.getLogger(__name__)

    async def rerank(
        self,
        query_text: str,
        candidates: list[RetrievedSource],
    ) -> list[RerankHit]:
        try:
            return await self._primary.rerank(query_text, candidates)
        except ModelProviderError as exc:
            # Query/document text is intentionally excluded from logs.
            self._logger.warning(
                "reranker_fallback provider=%s model=%s code=%s candidates=%d",
                exc.provider,
                exc.model,
                exc.code,
                len(candidates),
            )
            return await self._fallback.rerank(query_text, candidates)
