import pytest

from app.schemas.knowledge import KnowledgeChunk
from app.schemas.vector_search import VectorSearchHit
from app.services.retrieval.source_resolver import resolve_search_hits


def chunk(chunk_id: str, section: str = "Checks") -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=chunk_id,
        doc_id="doc-1",
        title="Sensor guide",
        section_title=section,
        source_url="https://example.com/guide",
        text=f"Evidence for {chunk_id}",
        safety_notes=["Qualified personnel only."],
    )


def hit(chunk_id: str, score: float) -> VectorSearchHit:
    return VectorSearchHit(chunk_id=chunk_id, score=score)


def test_resolves_hit_order_score_text_and_metadata_without_modifying_inputs() -> None:
    chunks = [chunk("chunk-a", "Principle"), chunk("chunk-b", "Checks")]
    hits = [hit("chunk-b", 0.9), hit("chunk-a", 0.7)]
    before = ([item.model_dump() for item in hits], [item.model_dump() for item in chunks])

    sources = resolve_search_hits(hits, chunks)

    assert [source.chunk_id for source in sources] == ["chunk-b", "chunk-a"]
    assert [source.score for source in sources] == [0.9, 0.7]
    assert sources[0].text == "Evidence for chunk-b"
    assert sources[0].section_title == "Checks"
    assert sources[0].source_url == "https://example.com/guide"
    assert sources[0].topic is None
    assert sources[0].pid_tags == []
    assert ([item.model_dump() for item in hits], [item.model_dump() for item in chunks]) == before


def test_empty_hits_return_empty_even_when_chunks_exist() -> None:
    assert resolve_search_hits([], [chunk("chunk-a")]) == []


def test_empty_hits_still_reject_duplicate_knowledge_ids() -> None:
    with pytest.raises(ValueError, match="Duplicate knowledge"):
        resolve_search_hits([], [chunk("duplicate"), chunk("duplicate")])


def test_rejects_hit_for_missing_chunk() -> None:
    with pytest.raises(ValueError, match="missing chunk ID: missing"):
        resolve_search_hits([hit("missing", 0.8)], [chunk("chunk-a")])


def test_rejects_duplicate_search_hits() -> None:
    with pytest.raises(ValueError, match="Duplicate search hit"):
        resolve_search_hits(
            [hit("chunk-a", 0.9), hit("chunk-a", 0.8)],
            [chunk("chunk-a")],
        )


def test_returned_sources_do_not_share_mutable_optional_metadata() -> None:
    sources = resolve_search_hits(
        [hit("chunk-a", 0.9), hit("chunk-b", 0.8)],
        [chunk("chunk-a"), chunk("chunk-b")],
    )
    sources[0].pid_tags.append("MAF")
    assert sources[1].pid_tags == []
