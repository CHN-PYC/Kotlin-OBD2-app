import asyncio
from collections.abc import Iterable

import pytest

from app.providers.errors import ModelServerError
from app.providers.fastembed_reranker import FastEmbedCrossEncoder
from app.schemas.reranking import RerankPair


class FakeRuntime:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.calls: list[tuple[str, list[str], int]] = []

    def rerank(
        self,
        query: str,
        documents: Iterable[str],
        batch_size: int = 64,
        **kwargs: object,
    ) -> Iterable[float]:
        document_list = list(documents)
        self.calls.append((query, document_list, batch_size))
        return self.scores


def test_scores_pairs_and_reuses_lazy_runtime() -> None:
    runtime = FakeRuntime([0.2, 0.9])
    loads = 0

    def factory() -> FakeRuntime:
        nonlocal loads
        loads += 1
        return runtime

    model = FastEmbedCrossEncoder(
        model_name="test-reranker",
        batch_size=4,
        runtime_factory=factory,
    )
    pairs = [
        RerankPair(query_text="query", document_text="first"),
        RerankPair(query_text="query", document_text="second"),
    ]

    first = asyncio.run(model.score_pairs(pairs))
    second = asyncio.run(model.score_pairs(pairs))

    assert loads == 1
    assert first.scores == second.scores == [0.2, 0.9]
    assert runtime.calls == [
        ("query", ["first", "second"], 4),
        ("query", ["first", "second"], 4),
    ]


def test_maps_runtime_failure_without_exposing_documents() -> None:
    class BrokenRuntime(FakeRuntime):
        def rerank(
            self,
            query: str,
            documents: Iterable[str],
            batch_size: int = 64,
            **kwargs: object,
        ) -> Iterable[float]:
            raise RuntimeError("private document content")

    model = FastEmbedCrossEncoder(
        model_name="test-reranker",
        batch_size=4,
        runtime_factory=lambda: BrokenRuntime([]),
    )
    with pytest.raises(ModelServerError) as caught:
        asyncio.run(
            model.score_pairs([RerankPair(query_text="query", document_text="private")])
        )

    assert "private document content" not in str(caught.value)


def test_rejects_mixed_queries_before_runtime_load() -> None:
    model = FastEmbedCrossEncoder(
        model_name="test-reranker",
        batch_size=4,
        runtime_factory=lambda: pytest.fail("runtime must not load"),
    )
    with pytest.raises(ValueError, match="shared query"):
        asyncio.run(
            model.score_pairs(
                [
                    RerankPair(query_text="first", document_text="a"),
                    RerankPair(query_text="second", document_text="b"),
                ]
            )
        )
