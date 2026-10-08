import asyncio

from app.providers.embedding import EmbeddingRequest, EmbeddingResult
from app.schemas.knowledge import KnowledgeChunk
from app.services.knowledge.ingestion import KnowledgeIngestionService
from app.services.retrieval.memory_vector_store import MemoryVectorStore


class FakeEmbeddingModel:
    provider_name = "fake"
    model_name = "fake-embedding"

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        vectors = [[1.0, float(index + 1)] for index, _ in enumerate(request.texts)]
        return EmbeddingResult(provider="fake", model="fake-embedding", vectors=vectors)


def chunk(chunk_id: str) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=chunk_id,
        doc_id="doc",
        title="Guide",
        section_title="Checks",
        source_url="https://example.com",
        text=f"Evidence {chunk_id}",
    )


def test_ingestion_batches_embeddings_and_makes_chunks_searchable() -> None:
    async def scenario() -> None:
        store = MemoryVectorStore(dimension=2)
        service = KnowledgeIngestionService(
            embedding_model=FakeEmbeddingModel(),
            vector_store=store,
            expected_dimension=2,
            batch_size=2,
        )
        report = await service.ingest([chunk("a"), chunk("b"), chunk("c")])

        assert report.chunk_count == 3
        assert report.batch_count == 2
        assert {item.chunk_id for item in await store.search([1.0, 1.0], k=3)} == {
            "a",
            "b",
            "c",
        }

    asyncio.run(scenario())


def test_ingestion_rejects_duplicate_ids_before_embedding() -> None:
    service = KnowledgeIngestionService(
        embedding_model=FakeEmbeddingModel(),
        vector_store=MemoryVectorStore(dimension=2),
        expected_dimension=2,
    )
    try:
        asyncio.run(service.ingest([chunk("same"), chunk("same")]))
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate IDs must fail")
