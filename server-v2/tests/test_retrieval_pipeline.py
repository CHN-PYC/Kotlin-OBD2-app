import asyncio

import pytest

from app.providers.errors import ModelServerError
from app.schemas.reranking import RerankHit
from app.schemas.retrieval import RetrievedSource
from app.schemas.vector_store import VectorRecord
from app.services.retrieval.reranking import PassThroughReranker, ResilientReranker
from app.services.retrieval.retrieval_pipeline import RetrievalPipeline


def source(chunk_id: str, score: float) -> RetrievedSource:
    return RetrievedSource(
        chunk_id=chunk_id,
        doc_id="doc",
        title="Guide",
        source_url="https://example.com",
        score=score,
        text=f"Evidence {chunk_id}",
        section_title="Checks",
    )


class FakeVectorStore:
    def __init__(self, sources: list[RetrievedSource]) -> None:
        self.sources = sources
        self.received_k: int | None = None

    async def upsert(self, records: list[VectorRecord]) -> None:
        raise AssertionError("pipeline must not write to the vector store")

    async def search(self, query_vector: list[float], *, k: int) -> list[RetrievedSource]:
        self.received_k = k
        return [item.model_copy(deep=True) for item in self.sources[:k]]

    async def delete(self, chunk_ids: list[str]) -> None:
        raise AssertionError("pipeline must not delete from the vector store")


class ReverseReranker:
    def __init__(self) -> None:
        self.received_query: str | None = None

    async def rerank(self, query_text: str, candidates: list[RetrievedSource]) -> list[RerankHit]:
        self.received_query = query_text
        size = len(candidates)
        return [
            RerankHit(chunk_id=item.chunk_id, score=float(size - index))
            for index, item in enumerate(reversed(candidates))
        ]


class FakeLexicalRetriever:
    def __init__(self, sources: list[RetrievedSource]) -> None:
        self.sources = sources

    async def search(self, query_text: str, *, k: int) -> list[RetrievedSource]:
        return [item.model_copy(deep=True) for item in self.sources[:k]]


def test_retrieves_candidate_k_reranks_then_returns_final_k_with_both_scores() -> None:
    retriever = FakeVectorStore([source("a", 0.9), source("b", 0.8), source("c", 0.7)])
    reranker = ReverseReranker()
    pipeline = RetrievalPipeline(retriever, reranker)
    results = asyncio.run(
        pipeline.retrieve(
            "Which check comes first?",
            [1.0, 0.0],
            candidate_k=3,
            final_k=2,
        )
    )
    assert retriever.received_k == 3
    assert reranker.received_query == "Which check comes first?"
    assert [item.source.chunk_id for item in results] == ["c", "b"]
    assert [item.source.score for item in results] == [0.7, 0.8]
    assert [item.rerank_score for item in results] == [3.0, 2.0]


def test_pass_through_baseline_preserves_dense_order_and_scores() -> None:
    pipeline = RetrievalPipeline(
        FakeVectorStore([source("a", 0.9), source("b", 0.8)]), PassThroughReranker()
    )
    results = asyncio.run(pipeline.retrieve("query", [1.0], candidate_k=2, final_k=1))
    assert results[0].source.chunk_id == "a"
    assert results[0].source.score == results[0].rerank_score == 0.9
    assert results[0].rerank_provider == "pass_through"


def test_hybrid_pipeline_preserves_rrf_order_through_pass_through_reranker() -> None:
    dense = [source("dense-only", 0.9), source("both", 0.8)]
    lexical = [source("both", 9.0), source("lexical-only", 8.0)]
    pipeline = RetrievalPipeline(
        FakeVectorStore(dense),
        PassThroughReranker(),
        FakeLexicalRetriever(lexical),
    )

    results = asyncio.run(pipeline.retrieve("P0171", [1.0], candidate_k=3, final_k=3))

    assert [item.source.chunk_id for item in results] == [
        "both",
        "dense-only",
        "lexical-only",
    ]
    assert results[-1].source.score == 0.0


def test_reranker_provider_failure_falls_back_to_dense_order() -> None:
    class FailedReranker:
        async def rerank(
            self, query_text: str, candidates: list[RetrievedSource]
        ) -> list[RerankHit]:
            raise ModelServerError("failed", provider="fake", model="reranker")

    pipeline = RetrievalPipeline(
        FakeVectorStore([source("a", 0.9), source("b", 0.8)]),
        ResilientReranker(FailedReranker(), PassThroughReranker()),
    )
    results = asyncio.run(pipeline.retrieve("query", [1.0], candidate_k=2, final_k=2))

    assert [item.source.chunk_id for item in results] == ["a", "b"]
    assert {item.rerank_provider for item in results} == {"pass_through"}


def test_empty_retrieval_skips_reranker() -> None:
    class MustNotRun:
        async def rerank(
            self, query_text: str, candidates: list[RetrievedSource]
        ) -> list[RerankHit]:
            pytest.fail("Reranker must not run without candidates")

    result = asyncio.run(
        RetrievalPipeline(FakeVectorStore([]), MustNotRun()).retrieve(
            "query",
            [1.0],
            candidate_k=5,
            final_k=2,
        )
    )
    assert result == []


@pytest.mark.parametrize("candidate_k,final_k", [(0, 1), (2, 0), (1, 2), (2.0, 1), (2, True)])
def test_rejects_invalid_k_before_retrieval(candidate_k: object, final_k: object) -> None:
    pipeline = RetrievalPipeline(FakeVectorStore([]), PassThroughReranker())
    with pytest.raises(ValueError):
        asyncio.run(
            pipeline.retrieve(
                "query",
                [1.0],
                candidate_k=candidate_k,
                final_k=final_k,  # type: ignore[arg-type]
            )
        )


def test_rejects_blank_query_before_retrieval() -> None:
    retriever = FakeVectorStore([])
    with pytest.raises(ValueError, match="blank"):
        asyncio.run(
            RetrievalPipeline(retriever, PassThroughReranker()).retrieve(
                " ",
                [1.0],
                candidate_k=2,
                final_k=1,
            )
        )
    assert retriever.received_k is None


@pytest.mark.parametrize(
    "hits",
    [
        [RerankHit(chunk_id="a", score=1.0)],
        [RerankHit(chunk_id="a", score=1.0), RerankHit(chunk_id="a", score=0.0)],
        [RerankHit(chunk_id="a", score=1.0), RerankHit(chunk_id="unknown", score=0.0)],
    ],
)
def test_rejects_missing_duplicate_or_unknown_rerank_ids(hits: list[RerankHit]) -> None:
    class BadReranker:
        async def rerank(
            self, query_text: str, candidates: list[RetrievedSource]
        ) -> list[RerankHit]:
            return hits

    pipeline = RetrievalPipeline(
        FakeVectorStore([source("a", 0.9), source("b", 0.8)]), BadReranker()
    )
    with pytest.raises(ValueError):
        asyncio.run(pipeline.retrieve("query", [1.0], candidate_k=2, final_k=1))
