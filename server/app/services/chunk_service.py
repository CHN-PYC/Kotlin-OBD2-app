from app.models.kb_chunk import KnowledgeChunk


class ChunkService:
    def split_document(
        self,
        *,
        doc_id: str,
        title: str,
        topic: str,
        pid_tags: list[str],
        source_url: str | None,
        text: str,
        chunk_size: int = 600,
        overlap: int = 120,
    ) -> list[KnowledgeChunk]:
        normalized = " ".join(text.split())
        if not normalized:
            return []

        chunks: list[KnowledgeChunk] = []
        start = 0
        idx = 0
        while start < len(normalized):
            end = min(len(normalized), start + chunk_size)
            chunk_text = normalized[start:end].strip()
            if chunk_text:
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"{doc_id}_chunk_{idx:04d}",
                        doc_id=doc_id,
                        title=title,
                        topic=topic,
                        pid_tags=pid_tags,
                        source_url=source_url,
                        chunk_index=idx,
                        text=chunk_text,
                        token_count=len(chunk_text.split()),
                    )
                )
                idx += 1
            if end == len(normalized):
                break
            start = max(0, end - overlap)
        return chunks
