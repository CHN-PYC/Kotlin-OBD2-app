from app.contracts.vector_store import VectorStore
from app.providers.embedding import EmbeddingModel, EmbeddingRequest
from app.schemas.knowledge import IngestionReport, KnowledgeChunk
from app.schemas.vector_store import VectorRecord
from app.services.retrieval.embedding_validation import validate_embedding_result


class KnowledgeIngestionService:
    def __init__(
        self,
        *,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        expected_dimension: int,
        batch_size: int = 16,
    ) -> None:
        if type(batch_size) is not int or batch_size <= 0:
            raise ValueError("batch_size must be a positive integer")
        if type(expected_dimension) is not int or expected_dimension <= 0:
            raise ValueError("expected_dimension must be a positive integer")
        self._embedding_model = embedding_model
        self._vector_store = vector_store
        self._expected_dimension = expected_dimension
        self._batch_size = batch_size

    async def ingest(self, chunks: list[KnowledgeChunk]) -> IngestionReport:
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("ingestion input must not contain duplicate chunk IDs")

        batch_count = 0
        for start in range(0, len(chunks), self._batch_size):
            batch = chunks[start : start + self._batch_size]
            # LEARNING: batching controls request memory and latency; it does not change
            # vector dimensions. Re-ingestion is safe because chunk_id maps to a stable ID.
            request = EmbeddingRequest(texts=[chunk.text for chunk in batch])
            result = validate_embedding_result(
                request,
                await self._embedding_model.embed(request),
                expected_dimension=self._expected_dimension,
            )
            records = [
                VectorRecord(vector=vector, chunk=chunk)
                for chunk, vector in zip(batch, result.vectors, strict=True)
            ]
            await self._vector_store.upsert(records)
            batch_count += 1

        return IngestionReport(
            provider=self._embedding_model.provider_name,
            model=self._embedding_model.model_name,
            chunk_count=len(chunks),
            batch_count=batch_count,
        )
