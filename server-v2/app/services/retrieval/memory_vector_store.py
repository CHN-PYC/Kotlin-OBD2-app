from app.contracts.vector_store import VectorStore
from app.schemas.retrieval import RetrievedSource
from app.schemas.vector_search import IndexedVector
from app.schemas.vector_store import VectorRecord
from app.services.retrieval.source_resolver import resolve_search_hits
from app.services.retrieval.top_k_search import search_top_k


class MemoryVectorStore(VectorStore):
    def __init__(self, *, dimension: int) -> None:
        if type(dimension) is not int or dimension <= 0:
            raise ValueError("dimension must be a positive integer")
        self._dimension = dimension
        self._records: dict[str, VectorRecord] = {}

    async def upsert(self, records: list[VectorRecord]) -> None:
        incoming: dict[str, VectorRecord] = {}
        for record in records:
            chunk_id = record.chunk.chunk_id
            if chunk_id in incoming:
                raise ValueError("upsert batch must not contain duplicate chunk IDs")
            if len(record.vector) != self._dimension:
                raise ValueError(f"vector dimension must be {self._dimension}")
            if not any(value != 0.0 for value in record.vector):
                raise ValueError("vector must not be all zero")
            incoming[chunk_id] = record.model_copy(deep=True)

        # Update only after the whole batch passes validation, so failure writes nothing.
        self._records.update(incoming)

    async def search(self, query_vector: list[float], *, k: int) -> list[RetrievedSource]:
        indexed_vectors = [
            IndexedVector(chunk_id=chunk_id, vector=record.vector)
            for chunk_id, record in self._records.items()
        ]
        hits = search_top_k(query_vector, indexed_vectors, k=k)
        chunks = [record.chunk for record in self._records.values()]
        return resolve_search_hits(hits, chunks)

    async def delete(self, chunk_ids: list[str]) -> None:
        if any(type(chunk_id) is not str or not chunk_id.strip() for chunk_id in chunk_ids):
            raise ValueError("chunk IDs must be non-blank strings")

        for chunk_id in set(chunk_ids):
            self._records.pop(chunk_id, None)

    async def aclose(self) -> None:
        """Memory storage owns no external resource."""
