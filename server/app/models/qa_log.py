from pydantic import BaseModel, Field
from typing import List


class QaLog(BaseModel):
    qa_id: str
    session_id: str
    question: str
    rewritten_query: str
    retrieved_chunk_ids: List[str] = Field(default_factory=list)
    answer: str
    severity: str
    sources: List[str] = Field(default_factory=list)
    created_at: str
