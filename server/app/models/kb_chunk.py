from pydantic import BaseModel, Field
from typing import List, Optional


class KnowledgeChunk(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    topic: str
    pid_tags: List[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    chunk_index: int
    text: str
    token_count: Optional[int] = None
