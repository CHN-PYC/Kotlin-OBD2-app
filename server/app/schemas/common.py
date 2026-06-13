from pydantic import BaseModel, Field
from typing import List, Optional


class RetrievedSource(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    source_url: str
    score: float
    text: str
    topic: Optional[str] = None
    pid_tags: List[str] = Field(default_factory=list)
