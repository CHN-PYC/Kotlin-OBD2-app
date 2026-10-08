import pytest
from pydantic import ValidationError

from app.schemas.knowledge import KnowledgeChunk
from app.services.knowledge.chunk_builder import build_section_chunks
from app.services.knowledge.html_extractor import ExtractedArticle, TextBlock


def article() -> ExtractedArticle:
    return ExtractedArticle(
        title="Sensor",
        safety_notes=["Qualified personnel only."],
        blocks=[
            TextBlock(heading_path=["Sensor"], kind="paragraph", text="Introduction"),
            TextBlock(heading_path=["Sensor", "Principle"], kind="paragraph", text="Function"),
            TextBlock(
                heading_path=["Sensor", "Checks", "Supply"], kind="paragraph", text="Inspect supply"
            ),
        ],
    )


def test_builds_chunks_with_source_ids_and_safety_context() -> None:
    source = article()
    before = source.model_dump()
    chunks = build_section_chunks(source, doc_id=" doc-1 ", source_url=" https://example.com ")
    assert [c.chunk_id for c in chunks] == ["doc-1:section:1", "doc-1:section:2"]
    assert [c.section_title for c in chunks] == ["Principle", "Checks"]
    for chunk in chunks:
        assert chunk.doc_id == "doc-1"
        assert chunk.source_url == "https://example.com"
        assert chunk.title == "Sensor"
        assert chunk.safety_notes == source.safety_notes
        assert "Safety: Qualified personnel only." in chunk.text
        assert "score" not in chunk.model_dump()
    assert chunks[1].text.endswith("Supply\n\nInspect supply")
    chunks[0].safety_notes.append("Local change")
    assert chunks[1].safety_notes == source.safety_notes
    assert source.model_dump() == before


def test_returns_no_chunks_for_empty_article() -> None:
    source = article().model_copy(update={"blocks": []})
    assert build_section_chunks(source, doc_id="doc", source_url="https://example.com") == []


@pytest.mark.parametrize("doc_id,source_url", [(" ", "https://example.com"), ("doc", " ")])
def test_rejects_blank_source_even_for_empty_article(doc_id: str, source_url: str) -> None:
    with pytest.raises(ValueError):
        build_section_chunks(
            article().model_copy(update={"blocks": []}), doc_id=doc_id, source_url=source_url
        )


def test_rejects_inconsistent_document_title() -> None:
    source = article().model_copy(update={"title": "Different document"})
    with pytest.raises(ValueError):
        build_section_chunks(source, doc_id="doc", source_url="https://example.com")


def test_chunk_schema_rejects_blank_text() -> None:
    with pytest.raises(ValidationError):
        KnowledgeChunk(
            chunk_id="c",
            doc_id="d",
            title="Sensor",
            section_title="Checks",
            source_url="https://example.com",
            text=" ",
        )


def test_chunk_schema_uses_independent_safety_lists() -> None:
    values = {
        "chunk_id": "c",
        "doc_id": "d",
        "title": "Sensor",
        "section_title": "Checks",
        "source_url": "https://example.com",
        "text": "Evidence",
    }
    first = KnowledgeChunk(**values)
    second = KnowledgeChunk(**values)
    first.safety_notes.append("Note")
    assert second.safety_notes == []


def test_rejects_empty_heading_path() -> None:
    source = article()
    source.blocks[1].heading_path = []
    with pytest.raises(ValueError):
        build_section_chunks(source, doc_id="doc", source_url="https://example.com")


def test_returns_no_chunks_for_introduction_only() -> None:
    source = article()
    source.blocks = source.blocks[:1]
    assert build_section_chunks(source, doc_id="doc", source_url="https://example.com") == []
