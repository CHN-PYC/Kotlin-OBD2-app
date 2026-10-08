from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.providers.embedding import EmbeddingVector


class IndexedVector(BaseModel):
    """One knowledge vector and the stable chunk identifier it belongs to."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    chunk_id: str = Field(min_length=1)
    vector: EmbeddingVector


class VectorSearchHit(BaseModel):
    """A ranked vector match; source text is resolved in the next stage."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    chunk_id: str = Field(min_length=1)
    score: Annotated[float, Field(strict=True, ge=-1, le=1, allow_inf_nan=False)]
