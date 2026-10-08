from typing import Annotated, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Constrain each item, not just the length of the surrounding list.
EmbeddingText = Annotated[str, Field(strict=True, min_length=1)]
VectorValue = Annotated[float, Field(strict=True, allow_inf_nan=False)]
EmbeddingVector = Annotated[list[VectorValue], Field(min_length=1)]


class EmbeddingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texts: list[EmbeddingText] = Field(min_length=1)

    @field_validator("texts")
    @classmethod
    def reject_blank_texts(cls, texts: list[str]) -> list[str]:
        if any(not text.strip() for text in texts):
            raise ValueError("Embedding texts must not be blank")
        # Preserve exactly what was token-counted; do not silently trim the inputs.
        return texts


class EmbeddingResult(BaseModel):
    """Basic response shape; cross-request count/dimension checks are separate."""

    model_config = ConfigDict(extra="forbid")
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    vectors: list[EmbeddingVector] = Field(min_length=1)


@runtime_checkable
class EmbeddingModel(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Return one vector per input text, in the same order."""
        ...
