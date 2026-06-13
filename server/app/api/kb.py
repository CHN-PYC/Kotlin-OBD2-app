from fastapi import APIRouter
from app.repositories.kb_repository import KbRepository
from app.schemas.kb import (
    KnowledgeDocumentIngestRequest,
    KnowledgeDocumentResponse,
    KnowledgeStatusResponse,
)
from app.services.ingestion_service import IngestionService
from app.services.vector_store_service import VectorStoreService

router = APIRouter(prefix="/kb", tags=["kb"])
service = IngestionService()
repo = KbRepository()
vector_store = VectorStoreService()


@router.post("/documents", response_model=KnowledgeDocumentResponse)
def ingest_document(request: KnowledgeDocumentIngestRequest) -> KnowledgeDocumentResponse:
    return service.ingest_document(request)


@router.post("/rebuild")
def rebuild_index() -> dict:
    service.rebuild_index()
    return {"ok": True}


@router.get("/documents")
def list_documents() -> list[dict]:
    return [item.model_dump() for item in repo.list_documents()]


@router.get("/status", response_model=KnowledgeStatusResponse)
def status() -> KnowledgeStatusResponse:
    return KnowledgeStatusResponse(
        document_count=len(repo.list_documents()),
        chunk_count=len(repo.list_chunks()),
        index_exists=vector_store.index_exists(),
    )
