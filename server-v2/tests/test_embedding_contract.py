import asyncio

import pytest
from pydantic import ValidationError

from app.providers.embedding import EmbeddingModel, EmbeddingRequest, EmbeddingResult


class FakeEmbeddingModel:
    provider_name = "fake"
    model_name = "fake-embedding"

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        # Test vectors encode position only; these are not semantic embeddings.
        return EmbeddingResult(
            provider=self.provider_name,
            model=self.model_name,
            vectors=[[float(index), 1.0] for index, _ in enumerate(request.texts)],
        )


def test_request_preserves_text_and_order() -> None:
    texts = ["  First evidence  ", "Second evidence"]
    assert EmbeddingRequest(texts=texts).texts == texts


@pytest.mark.parametrize("texts", [[], [""], [" \n"], ["valid", " "], [123]])
def test_rejects_empty_or_invalid_texts(texts: list) -> None:
    with pytest.raises(ValidationError):
        EmbeddingRequest(texts=texts)


def test_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        EmbeddingRequest.model_validate({"texts": ["Evidence"], "temperature": 0})


def test_result_accepts_finite_vectors() -> None:
    result = EmbeddingResult(provider="fake", model="test", vectors=[[0.2, -0.5]])
    assert result.vectors == [[0.2, -0.5]]


@pytest.mark.parametrize(
    "vectors",
    [
        [],
        [[]],
        [[float("nan")]],
        [[float("inf")]],
        [[float("-inf")]],
        [["0.2"]],
        [[True]],
    ],
)
def test_result_rejects_empty_or_invalid_vectors(vectors: list) -> None:
    with pytest.raises(ValidationError):
        EmbeddingResult(provider="fake", model="test", vectors=vectors)


def test_fake_model_satisfies_protocol_and_preserves_batch_order() -> None:
    model = FakeEmbeddingModel()
    request = EmbeddingRequest(texts=["First", "Second"])
    result = asyncio.run(model.embed(request))
    assert isinstance(model, EmbeddingModel)
    assert result.vectors == [[0.0, 1.0], [1.0, 1.0]]
    assert result.provider == "fake"
