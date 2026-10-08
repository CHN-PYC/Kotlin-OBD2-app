from pydantic import BaseModel, ConfigDict, Field


class RetrievalEvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    case_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    relevant_chunk_ids: set[str] = Field(min_length=1)


class RetrievalMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_count: int = Field(ge=1)
    k: int = Field(ge=1)
    hit_at_k: float = Field(ge=0, le=1)
    recall_at_k: float = Field(ge=0, le=1)
    precision_at_k: float = Field(ge=0, le=1)
    mrr: float = Field(ge=0, le=1)
