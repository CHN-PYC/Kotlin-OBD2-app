from app.schemas.knowledge import KnowledgeChunk
from app.services.knowledge import section_grouper, section_renderer
from app.services.knowledge.html_extractor import ExtractedArticle


def build_section_chunks(
    article: ExtractedArticle, *, doc_id: str, source_url: str
) -> list[KnowledgeChunk]:
    """Build candidate chunks with sequential IDs; no embeddings or persistence.

    Strip doc_id/source_url and reject blank values even when the article is empty.
    Group article.blocks using group_section_blocks, then render each group with
    render_section. IDs use '{doc_id}:section:{number}', starting at 1.
    Reject blocks whose document heading differs from article.title.
    Return [] when no section groups exist. Do not mutate the article.
    """
    # Validate before looping so an empty article cannot hide invalid source data.
    doc_id = doc_id.strip()
    source_url = source_url.strip()
    if not doc_id or not source_url:
        raise ValueError("Document ID and source URL must not be blank")
    for block in article.blocks:
        if not block.heading_path or block.heading_path[0] != article.title:
            raise ValueError("Block document heading must match the article title")

    groups = section_grouper.group_section_blocks(article.blocks)
    chunks: list[KnowledgeChunk] = []
    for number, group in enumerate(groups, start=1):
        text = section_renderer.render_section(group, safety_notes=article.safety_notes)
        # KnowledgeChunk is the class; chunk is one validated instance, not a dict.
        chunk = KnowledgeChunk(
            chunk_id=f"{doc_id}:section:{number}",
            doc_id=doc_id,
            title=article.title,
            section_title=group[0].heading_path[1],
            source_url=source_url,
            text=text,
            safety_notes=article.safety_notes,
        )
        chunks.append(chunk)
    return chunks
