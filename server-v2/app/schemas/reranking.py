from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.retrieval import RetrievedSource


class RerankHit(BaseModel):
    """A reranker's score for one immutable retrieval candidate."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    chunk_id: str = Field(min_length=1)
    score: Annotated[float, Field(strict=True, allow_inf_nan=False)]
    rerank_provider: str = Field(default="unspecified", min_length=1)


class RerankedSource(BaseModel):
    """Keep dense retrieval score in source.score and the rerank score separately."""

    model_config = ConfigDict(extra="forbid")
    source: RetrievedSource
    rerank_score: Annotated[float, Field(strict=True, allow_inf_nan=False)]
    rerank_provider: str = Field(default="unspecified", min_length=1)


class RerankPair(BaseModel):
    """One query-document pair consumed by a Cross-Encoder."""

    model_config = ConfigDict(extra="forbid")
    query_text: str = Field(strict=True, min_length=1)
    document_text: str = Field(strict=True, min_length=1)


class RerankModelResult(BaseModel):
    """Scores must correspond to input pairs by position."""

    model_config = ConfigDict(extra="forbid")
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    scores: list[Annotated[float, Field(strict=True, allow_inf_nan=False)]]
