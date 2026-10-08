from pydantic import BaseModel

from app.providers.embedding import EmbeddingVector
from app.schemas.knowledge import KnowledgeChunk


class VectorRecord(BaseModel):
    vector: EmbeddingVector
    chunk: KnowledgeChunk
