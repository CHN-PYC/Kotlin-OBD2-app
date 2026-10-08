"""Compare dense retrieval with the configured reranker on labeled queries."""

import asyncio
import json
from pathlib import Path
from time import perf_counter

import httpx2
from pydantic import TypeAdapter

from app.contracts.vector_store import VectorStore
from app.core.config import RerankerProvider, Settings
from app.providers.factory import create_embedding_model, create_reranker, create_vector_store
from app.schemas.evaluation import RetrievalEvalCase
from app.services.knowledge.corpus_loader import load_curated_corpus
from app.services.retrieval.bm25 import BM25Retriever
from app.services.retrieval.evaluation import evaluate_rankings
from app.services.retrieval.query_retrieval import QueryRetrievalService
from app.services.retrieval.reranking import PassThroughReranker, Reranker
from app.services.retrieval.retrieval_pipeline import RetrievalPipeline


async def evaluate(
    *,
    label: str,
    cases: list[RetrievalEvalCase],
    reranker: Reranker,
    settings: Settings,
    client: httpx2.AsyncClient,
    store: VectorStore,
    lexical_retriever: BM25Retriever | None = None,
) -> dict[str, object]:
    service = QueryRetrievalService(
        embedding_model=create_embedding_model(settings, client=client),
        pipeline=RetrievalPipeline(store, reranker, lexical_retriever),
        expected_dimension=settings.embedding_dimension,
        candidate_multiplier=settings.rag_candidate_multiplier,
    )
    rankings: dict[str, list[str]] = {}
    started = perf_counter()
    for case in cases:
        results = await service.retrieve(case.query, final_k=3)
        rankings[case.case_id] = [item.source.chunk_id for item in results]
    elapsed = perf_counter() - started
    metrics = evaluate_rankings(cases, rankings, k=3)
    return {
        "label": label,
        **metrics.model_dump(),
        "elapsed_seconds": round(elapsed, 3),
        "mean_latency_ms": round(elapsed * 1000 / len(cases), 1),
        "rankings": rankings,
    }


async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cases = TypeAdapter(list[RetrievalEvalCase]).validate_json(
        (root / "eval/retrieval_cases.json").read_text(encoding="utf-8")
    )
    settings = Settings()
    rerank_settings = settings.model_copy(
        update={"reranker_provider": RerankerProvider.FASTEMBED}
    )
    lexical_retriever = BM25Retriever(load_curated_corpus(root))
    async with httpx2.AsyncClient() as client:
        store = await create_vector_store(settings)
        try:
            reports = [
                await evaluate(
                    label="dense_baseline",
                    cases=cases,
                    reranker=PassThroughReranker(),
                    settings=settings,
                    client=client,
                    store=store,
                ),
                await evaluate(
                    label="hybrid_rrf",
                    cases=cases,
                    reranker=PassThroughReranker(),
                    settings=settings,
                    client=client,
                    store=store,
                    lexical_retriever=lexical_retriever,
                ),
                await evaluate(
                    label=f"hybrid_rrf+{rerank_settings.reranker_model}",
                    cases=cases,
                    reranker=create_reranker(rerank_settings),
                    settings=settings,
                    client=client,
                    store=store,
                    lexical_retriever=lexical_retriever,
                ),
            ]
            print(json.dumps(reports, ensure_ascii=False, indent=2))
        finally:
            await store.aclose()


if __name__ == "__main__":
    asyncio.run(main())
