"""Run a real Ollama -> Qdrant retrieval without calling the chat model."""

import argparse
import asyncio
import json

import httpx2

from app.core.config import RerankerProvider, Settings
from app.providers.factory import create_embedding_model, create_reranker, create_vector_store
from app.services.retrieval.query_retrieval import QueryRetrievalService
from app.services.retrieval.retrieval_pipeline import RetrievalPipeline


async def run(reranker_provider: RerankerProvider | None) -> None:
    settings = Settings()
    if reranker_provider is not None:
        settings = settings.model_copy(update={"reranker_provider": reranker_provider})
    async with httpx2.AsyncClient() as client:
        store = await create_vector_store(settings)
        try:
            service = QueryRetrievalService(
                embedding_model=create_embedding_model(settings, client=client),
                pipeline=RetrievalPipeline(
                    vector_store=store,
                    reranker=create_reranker(settings),
                ),
                expected_dimension=settings.embedding_dimension,
                candidate_multiplier=settings.rag_candidate_multiplier,
            )
            results = await service.retrieve("空气流量计异常应该怎么检查？", final_k=3)
            print(
                json.dumps(
                    [
                        {
                            "chunk_id": item.source.chunk_id,
                            "score": round(item.source.score, 4),
                            "rerank_score": round(item.rerank_score, 4),
                            "rerank_provider": item.rerank_provider,
                            "title": item.source.title,
                            "section": item.source.section_title,
                        }
                        for item in results
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
        finally:
            await store.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reranker",
        choices=[item.value for item in RerankerProvider],
        help="Override configured reranker for this smoke run",
    )
    args = parser.parse_args()
    provider = RerankerProvider(args.reranker) if args.reranker else None
    asyncio.run(run(provider))


if __name__ == "__main__":
    main()
