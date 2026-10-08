import pytest

from app.providers.embedding import EmbeddingRequest, EmbeddingResult
from app.providers.errors import InvalidModelResponseError
from app.services.retrieval.embedding_validation import validate_embedding_result


def result(vectors: list[list[float]]) -> EmbeddingResult:
    return EmbeddingResult(provider="fake", model="fake-embedding", vectors=vectors)


def test_accepts_matching_vectors_without_normalizing_or_modifying_them() -> None:
    request = EmbeddingRequest(texts=["First", "Second"])
    response = result([[3.0, 4.0], [0.0, -2.0]])
    before = response.model_dump()
    assert validate_embedding_result(request, response, expected_dimension=2) is response
    assert response.model_dump() == before
    assert request.texts == ["First", "Second"]


@pytest.mark.parametrize("vectors", [[[1.0, 0.0]], [[1.0, 0.0]] * 3])
def test_rejects_missing_or_extra_vectors(vectors: list[list[float]]) -> None:
    with pytest.raises(InvalidModelResponseError, match="count") as error:
        validate_embedding_result(
            EmbeddingRequest(texts=["First", "Second"]), result(vectors), expected_dimension=2
        )
    assert error.value.code == "invalid_response"
    assert error.value.retryable is False
    assert error.value.provider == "fake"


@pytest.mark.parametrize(
    "vectors",
    [
        [[1.0], [2.0]],
        [[1.0, 0.0], [2.0]],
        [[1.0, 2.0, 3.0], [1.0, 2.0, 3.0]],
    ],
)
def test_rejects_inconsistent_or_wrong_dimensions(vectors: list[list[float]]) -> None:
    with pytest.raises(InvalidModelResponseError, match="dimension"):
        validate_embedding_result(
            EmbeddingRequest(texts=["First", "Second"]), result(vectors), expected_dimension=2
        )


def test_rejects_all_zero_vector_even_after_a_valid_vector() -> None:
    with pytest.raises(InvalidModelResponseError, match="all zero"):
        validate_embedding_result(
            EmbeddingRequest(texts=["First", "Second"]),
            result([[1.0, 0.0], [0.0, -0.0]]),
            expected_dimension=2,
        )


@pytest.mark.parametrize("dimension", [0, -1])
def test_rejects_invalid_expected_dimension(dimension: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        validate_embedding_result(
            EmbeddingRequest(texts=["First"]), result([[1.0, 0.0]]), expected_dimension=dimension
        )
