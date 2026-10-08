from app.providers.embedding import EmbeddingRequest, EmbeddingResult
from app.providers.errors import InvalidModelResponseError


def validate_embedding_result(
    request: EmbeddingRequest,
    result: EmbeddingResult,
    *,
    expected_dimension: int,
) -> EmbeddingResult:
    """Validate batch shape for later cosine retrieval; do not alter the vectors."""
    if expected_dimension <= 0:
        raise ValueError("Expected embedding dimension must be positive")
    if len(result.vectors) != len(request.texts):
        raise InvalidModelResponseError(
            "Embedding vector count does not match input text count",
            provider=result.provider,
            model=result.model,
        )
    for vector in result.vectors:
        if len(vector) != expected_dimension:
            raise InvalidModelResponseError(
                "Embedding vector dimension does not match expected dimension",
                provider=result.provider,
                model=result.model,
            )
        # Zero entries are valid; an entirely zero vector cannot define cosine similarity.
        if not any(value != 0.0 for value in vector):
            raise InvalidModelResponseError(
                "Embedding vector must not be all zero",
                provider=result.provider,
                model=result.model,
            )
    return result
