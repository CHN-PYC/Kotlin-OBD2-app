import json
from pathlib import Path

from app.schemas.knowledge import KnowledgeChunk


def load_chunks(paths: list[Path]) -> list[KnowledgeChunk]:
    """Load curated exports and fail before embedding on ID collisions."""
    chunks: list[KnowledgeChunk] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        chunks.extend(KnowledgeChunk.model_validate(item) for item in payload["chunks"])

    chunk_ids = [chunk.chunk_id for chunk in chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError("knowledge files must not contain duplicate chunk IDs")
    return chunks


def load_curated_corpus(root: Path) -> list[KnowledgeChunk]:
    paths = sorted((root / "knowledge").glob("*.chunks.json"))
    if not paths:
        raise FileNotFoundError("no knowledge chunk files found")
    return load_chunks(paths)
