from app.schemas.kb import KnowledgeDocumentIngestRequest
from app.services.ingestion_service import IngestionService
from app.services.retrieval_service import RetrievalService


def test_retrieval_returns_seeded_chunk(tmp_path):
    ingestion = IngestionService()
    ingestion.kb_repository.clear()
    ingestion.ingest_document(KnowledgeDocumentIngestRequest(
        title="Fuel trim doc",
        topic="fuel_trim",
        pid_tags=["STFT", "LTFT"],
        raw_text="High positive fuel trim may indicate lean mixture and vacuum leak.",
    ))
    service = RetrievalService()
    rewritten, results = service.retrieve(
        question="Why is STFT high?",
        vehicle_context={"sessionSummary": {"avgStft1": 12.0}},
        rule_summary={"summary": "fuel trim elevated"},
        top_k=3,
    )
    assert "STFT" in rewritten or "fuel trim" in rewritten.lower()
    assert results
