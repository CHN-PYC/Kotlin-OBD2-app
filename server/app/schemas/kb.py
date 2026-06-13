from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional


class KnowledgeDocumentIngestRequest(BaseModel):
    title: str
    topic: str
    source_url: Optional[HttpUrl] = None
    pid_tags: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None


class KnowledgeDocumentResponse(BaseModel):
    doc_id: str
    title: str
    topic: str
    source_url: Optional[str] = None
    pid_tags: List[str] = Field(default_factory=list)
    chunk_count: int = 0
    created_at: str


class KnowledgeStatusResponse(BaseModel):
    document_count: int
    chunk_count: int
    index_exists: bool
