from app.schemas.knowledge import KnowledgeChunk
from app.schemas.retrieval import RetrievedSource
from app.schemas.vector_search import VectorSearchHit


def resolve_search_hits(
    hits: list[VectorSearchHit],
    chunks: list[KnowledgeChunk],
) -> list[RetrievedSource]:
    """Resolve ranked vector hits to source text while preserving hit order."""
    chunk_by_id: dict[str, KnowledgeChunk] = {}
    for chunk in chunks:
        if chunk.chunk_id in chunk_by_id:
            raise ValueError(f"Duplicate knowledge chunk ID: {chunk.chunk_id}")
        chunk_by_id[chunk.chunk_id] = chunk

    seen_hits: set[str] = set()
    sources: list[RetrievedSource] = []
    for hit in hits:
        if hit.chunk_id in seen_hits:
            raise ValueError(f"Duplicate search hit ID: {hit.chunk_id}")
        seen_hits.add(hit.chunk_id)
        resolved_chunk = chunk_by_id.get(hit.chunk_id)
        if resolved_chunk is None:
            raise ValueError(f"Search hit references missing chunk ID: {hit.chunk_id}")
        sources.append(
            RetrievedSource(
                chunk_id=resolved_chunk.chunk_id,
                doc_id=resolved_chunk.doc_id,
                title=resolved_chunk.title,
                source_url=resolved_chunk.source_url,
                score=hit.score,
                text=resolved_chunk.text,
                section_title=resolved_chunk.section_title,
            )
        )
    return sources
