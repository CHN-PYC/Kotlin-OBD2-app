from app.services.chunk_service import ChunkService


def test_split_document_returns_chunks():
    service = ChunkService()
    chunks = service.split_document(
        doc_id="doc1",
        title="Title",
        topic="coolant",
        pid_tags=["COOLANT"],
        source_url=None,
        text="coolant data " * 200,
        chunk_size=120,
        overlap=20,
    )
    assert len(chunks) > 1
    assert chunks[0].chunk_id.startswith("doc1_chunk_")
