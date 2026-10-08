from pydantic import BaseModel, ConfigDict, Field


class KnowledgeChunk(BaseModel):
    """Candidate knowledge unit before token-budget checks and indexing."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    chunk_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    section_title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    text: str = Field(min_length=1)
    safety_notes: list[str] = Field(default_factory=list)
    # Retrieval metadata is deliberately structured rather than buried in text.
    # Vector databases can filter these fields before/while searching, and traces
    # can explain why a chunk was eligible for a vehicle question.
    source_name: str | None = None
    language: str = Field(default="zh-CN", min_length=1)
    topic: str | None = None
    pid_tags: list[str] = Field(default_factory=list)
    dtc_codes: list[str] = Field(default_factory=list)
    vehicle_scope: str = Field(default="general", min_length=1)


class IngestionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    chunk_count: int = Field(ge=0)
    batch_count: int = Field(ge=0)
