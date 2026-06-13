from app.repositories.kb_repository import KbRepository
from app.schemas.common import RetrievedSource
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.services.query_rewrite_service import QueryRewriteService


class RetrievalService:
    def __init__(self) -> None:
        self.kb_repository = KbRepository()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()
        self.query_rewrite = QueryRewriteService()

    def retrieve(self, question: str, vehicle_context: dict, rule_summary: dict | None = None, top_k: int = 5) -> tuple[str, list[RetrievedSource]]:
        rewritten_query = self.query_rewrite.rewrite(question, vehicle_context, rule_summary)
        vectorizer = self.vector_store.load_vectorizer()
        query_vector = self.embedding_service.transform_query(rewritten_query, vectorizer) if vectorizer else []
        ranked = self.vector_store.search(query_vector, top_k=top_k)
        chunks = {chunk.chunk_id: chunk for chunk in self.kb_repository.list_chunks()}
        results: list[RetrievedSource] = []
        for chunk_id, score in ranked:
            chunk = chunks.get(chunk_id)
            if not chunk:
                continue
            results.append(
                RetrievedSource(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    title=chunk.title,
                    source_url=chunk.source_url or "",
                    score=score,
                    text=chunk.text,
                    topic=chunk.topic,
                    pid_tags=chunk.pid_tags,
                )
            )
        return rewritten_query, results
