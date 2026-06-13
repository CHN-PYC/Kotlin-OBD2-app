from pydantic import BaseModel, Field
from typing import List, Optional


class KnowledgeDocument(BaseModel):
    doc_id: str
    title: str
    source_url: Optional[str] = None
    topic: str
    pid_tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    raw_text_path: str
    cleaned_text_path: str
    created_at: str
