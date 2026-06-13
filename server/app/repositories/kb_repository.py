from pathlib import Path
from app.core.config import FAISS_DIR
from app.core.constants import DOC_METADATA_FILE, CHUNK_METADATA_FILE
from app.models.kb_document import KnowledgeDocument
from app.models.kb_chunk import KnowledgeChunk
from app.utils.json_utils import append_jsonl, read_jsonl


doc_path = FAISS_DIR / DOC_METADATA_FILE
chunk_path = FAISS_DIR / CHUNK_METADATA_FILE


class KbRepository:
    def save_document(self, document: KnowledgeDocument) -> None:
        append_jsonl(doc_path, [document.model_dump()])

    def save_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        append_jsonl(chunk_path, [chunk.model_dump() for chunk in chunks])

    def list_documents(self) -> list[KnowledgeDocument]:
        return [KnowledgeDocument(**item) for item in read_jsonl(doc_path)]

    def list_chunks(self) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(**item) for item in read_jsonl(chunk_path)]

    def clear(self) -> None:
        for path in [doc_path, chunk_path]:
            if path.exists():
                path.unlink()
