from pydantic import BaseModel, ConfigDict, Field


class RetrievedSource(BaseModel):
    model_config = ConfigDict(strict=True, str_strip_whitespace=True)
    chunk_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_url: str = Field(default="")
    score: float = Field(allow_inf_nan=False)
    # Internal ordering score. It is excluded from API serialization because it
    # may be cosine similarity, RRF, or another strategy-specific scale.
    rank_score: float | None = Field(default=None, allow_inf_nan=False, exclude=True)
    text: str = Field(min_length=1)
    topic: str | None = None
    pid_tags: list[str] = Field(default_factory=list)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    section_title: str | None = None
