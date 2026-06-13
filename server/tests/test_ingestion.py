from app.schemas.kb import KnowledgeDocumentIngestRequest
from app.services.ingestion_service import IngestionService


def test_ingest_document_creates_chunks():
    service = IngestionService()
    service.kb_repository.clear()
    result = service.ingest_document(KnowledgeDocumentIngestRequest(
        title="Coolant doc",
        topic="coolant",
        pid_tags=["COOLANT"],
        raw_text="Coolant overheating can come from radiator blockage thermostat or fan failure.",
    ))
    assert result.chunk_count >= 1
