from datetime import datetime, UTC
from uuid import uuid4
from urllib.request import urlopen
from app.core.config import RAW_DOCS_DIR, PROCESSED_DOCS_DIR
from app.models.kb_document import KnowledgeDocument
from app.repositories.kb_repository import KbRepository
from app.schemas.kb import KnowledgeDocumentIngestRequest, KnowledgeDocumentResponse
from app.services.chunk_service import ChunkService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.utils.html_extractor import extract_text_from_html
from app.utils.text_cleaner import clean_text


class IngestionService:
    def __init__(self) -> None:
        self.kb_repository = KbRepository()
        self.chunk_service = ChunkService()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()

    def ingest_document(self, request: KnowledgeDocumentIngestRequest) -> KnowledgeDocumentResponse:
        doc_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        raw_text = self._load_raw_text(request)
        cleaned_text = clean_text(raw_text)
        raw_path = RAW_DOCS_DIR / f"{doc_id}.txt"
        cleaned_path = PROCESSED_DOCS_DIR / f"{doc_id}.txt"
        raw_path.write_text(raw_text, encoding="utf-8")
        cleaned_path.write_text(cleaned_text, encoding="utf-8")

        document = KnowledgeDocument(
            doc_id=doc_id,
            title=request.title,
            source_url=str(request.source_url) if request.source_url else None,
            topic=request.topic,
            pid_tags=request.pid_tags,
            summary=cleaned_text[:220],
            raw_text_path=str(raw_path),
            cleaned_text_path=str(cleaned_path),
            created_at=created_at,
        )
        chunks = self.chunk_service.split_document(
            doc_id=doc_id,
            title=request.title,
            topic=request.topic,
            pid_tags=request.pid_tags,
            source_url=document.source_url,
            text=cleaned_text,
        )
        self.kb_repository.save_document(document)
        self.kb_repository.save_chunks(chunks)
        self.rebuild_index()
        return KnowledgeDocumentResponse(
            doc_id=doc_id,
            title=request.title,
            topic=request.topic,
            source_url=document.source_url,
            pid_tags=request.pid_tags,
            chunk_count=len(chunks),
            created_at=created_at,
        )

    def rebuild_index(self) -> None:
        chunks = self.kb_repository.list_chunks()
        bundle = self.embedding_service.fit_transform(chunk.text for chunk in chunks)
        self.vector_store.write_index(
            bundle.matrix,
            [chunk.chunk_id for chunk in chunks],
            bundle.vectorizer,
        )

    def _load_raw_text(self, request: KnowledgeDocumentIngestRequest) -> str:
        if request.raw_text:
            return request.raw_text
        if request.source_url:
            with urlopen(str(request.source_url)) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
            if "<html" in body.lower():
                return extract_text_from_html(body)
            return body
        raise ValueError("Either raw_text or source_url is required")
