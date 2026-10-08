from app.schemas.knowledge import KnowledgeChunk
from app.schemas.retrieval import RetrievedSource
from app.schemas.vector_search import IndexedVector
from app.services.retrieval.source_resolver import resolve_search_hits
from app.services.retrieval.top_k_search import search_top_k


class ExactDenseRetriever:
    """In-memory exact cosine retriever used as the explainable search baseline."""

    def __init__(
        self,
        vectors: list[IndexedVector],
        chunks: list[KnowledgeChunk],
    ) -> None:
        vector_ids = [item.chunk_id for item in vectors]
        chunk_ids = [item.chunk_id for item in chunks]
        if len(set(vector_ids)) != len(vector_ids):
            raise ValueError("Indexed vector IDs must be unique")
        if len(set(chunk_ids)) != len(chunk_ids):
            raise ValueError("Knowledge chunk IDs must be unique")
        if set(vector_ids) != set(chunk_ids):
            raise ValueError("Indexed vectors and knowledge chunks must contain the same IDs")

        if vectors:
            dimension = len(vectors[0].vector)
            for item in vectors:
                if len(item.vector) != dimension:
                    raise ValueError("All indexed vectors must have the same dimension")
                if not any(value != 0.0 for value in item.vector):
                    raise ValueError("Indexed vectors must not be all zero")

        # A retriever represents one consistent index snapshot, independent of caller mutation.
        self._vectors = tuple(item.model_copy(deep=True) for item in vectors)
        self._chunks = tuple(item.model_copy(deep=True) for item in chunks)

    def retrieve(self, query_vector: list[float], *, k: int) -> list[RetrievedSource]:
        hits = search_top_k(query_vector, list(self._vectors), k=k)
        return resolve_search_hits(hits, list(self._chunks))
