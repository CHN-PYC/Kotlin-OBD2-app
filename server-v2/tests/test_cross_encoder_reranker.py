import asyncio

import pytest

from app.schemas.reranking import RerankModelResult, RerankPair
from app.schemas.retrieval import RetrievedSource
from app.services.retrieval.reranking import CrossEncoderReranker


def source(chunk_id: str, text: str) -> RetrievedSource:
    return RetrievedSource(
        chunk_id=chunk_id,
        doc_id="doc",
        title="Guide",
        score=0.5,
        text=text,
    )


class FakeCrossEncoder:
    provider_name = "fake"
    model_name = "fake-reranker"

    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.received_pairs: list[RerankPair] = []

    async def score_pairs(self, pairs: list[RerankPair]) -> RerankModelResult:
        self.received_pairs = pairs
        return RerankModelResult(
            provider=self.provider_name,
            model=self.model_name,
            scores=self.scores,
        )


def test_builds_text_pairs_and_binds_scores_to_candidate_ids() -> None:
    model = FakeCrossEncoder([0.2, 0.9])
    reranker = CrossEncoderReranker(model)

    hits = asyncio.run(
        reranker.rerank(
            "Why is starting voltage low?",
            [source("battery", "Check battery voltage."), source("fuel", "Check fuel trim.")],
        )
    )

    assert [pair.model_dump() for pair in model.received_pairs] == [
        {
            "query_text": "Why is starting voltage low?",
            "document_text": "Check battery voltage.",
        },
        {
            "query_text": "Why is starting voltage low?",
            "document_text": "Check fuel trim.",
        },
    ]
    assert [(hit.chunk_id, hit.score) for hit in hits] == [("battery", 0.2), ("fuel", 0.9)]
    assert {hit.rerank_provider for hit in hits} == {"fake:fake-reranker"}


def test_empty_candidates_do_not_call_model() -> None:
    model = FakeCrossEncoder([])
    assert asyncio.run(CrossEncoderReranker(model).rerank("query", [])) == []
    assert model.received_pairs == []


def test_rejects_wrong_number_of_scores() -> None:
    model = FakeCrossEncoder([0.8])
    with pytest.raises(ValueError, match="one score per candidate"):
        asyncio.run(
            CrossEncoderReranker(model).rerank(
                "query",
                [source("a", "first"), source("b", "second")],
            )
        )


def test_rejects_blank_query_before_calling_model() -> None:
    model = FakeCrossEncoder([0.8])
    with pytest.raises(ValueError, match="blank"):
        asyncio.run(CrossEncoderReranker(model).rerank(" ", [source("a", "first")]))
    assert model.received_pairs == []
