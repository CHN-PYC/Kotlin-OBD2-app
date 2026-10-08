import asyncio
import json
from collections.abc import Callable

import httpx2
import pytest

from app.providers.embedding import EmbeddingModel, EmbeddingRequest, EmbeddingResult
from app.providers.errors import (
    InvalidModelResponseError,
    ModelConnectionError,
    ModelNotConfiguredError,
    ModelRateLimitError,
    ModelRequestError,
    ModelServerError,
    ModelTimeoutError,
)
from app.providers.ollama_embedding import OllamaEmbeddingModel


def run(handler: Callable[[httpx2.Request], httpx2.Response]) -> EmbeddingResult:
    async def call() -> EmbeddingResult:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            model = OllamaEmbeddingModel(
                base_url="http://ollama:11434/",
                model_name="bge-m3",
                expected_dimension=2,
                timeout_seconds=10,
                client=client,
            )
            assert isinstance(model, EmbeddingModel)
            try:
                return await model.embed(EmbeddingRequest(texts=[" First ", "Second"]))
            finally:
                await model.aclose()
                assert not client.is_closed

    return asyncio.run(call())


def test_maps_batch_request_and_response() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/embed"
        assert json.loads(request.content) == {
            "model": "bge-m3",
            "input": [" First ", "Second"],
            "truncate": False,
        }
        assert request.extensions["timeout"]["read"] == 10
        return httpx2.Response(
            200,
            json={
                "model": "bge-m3:latest",
                "embeddings": [[1.0, 0.0], [0.0, 2.0]],
                "prompt_eval_count": 9,
            },
        )

    response = run(handler)
    assert response.vectors == [[1.0, 0.0], [0.0, 2.0]]
    assert response.provider == "ollama"


def test_sends_optional_cpu_only_runtime_setting() -> None:
    async def call() -> None:
        def handler(request: httpx2.Request) -> httpx2.Response:
            assert json.loads(request.content)["options"] == {"num_gpu": 0}
            return httpx2.Response(
                200,
                json={"model": "bge-m3", "embeddings": [[1.0, 0.0]]},
            )

        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            model = OllamaEmbeddingModel(
                base_url="http://ollama:11434",
                model_name="bge-m3",
                expected_dimension=2,
                timeout_seconds=10,
                num_gpu=0,
                client=client,
            )
            await model.embed(EmbeddingRequest(texts=["query"]))

    asyncio.run(call())


@pytest.mark.parametrize(
    "status,error",
    [
        (400, ModelRequestError),
        (404, ModelRequestError),
        (429, ModelRateLimitError),
        (500, ModelServerError),
        (503, ModelServerError),
        (302, ModelRequestError),
    ],
)
def test_maps_status_without_exposing_body(status: int, error: type[Exception]) -> None:
    with pytest.raises(error) as caught:
        run(
            lambda request: httpx2.Response(
                status, json={"error": "private input"}, headers={"Location": "https://example.com"}
            )
        )
    assert "private input" not in str(caught.value)


@pytest.mark.parametrize(
    "error,expected",
    [
        (httpx2.ReadTimeout, ModelTimeoutError),
        (httpx2.ConnectError, ModelConnectionError),
        (httpx2.ReadError, ModelConnectionError),
    ],
)
def test_maps_transport_errors(error: type[httpx2.RequestError], expected: type[Exception]) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise error("Network failure", request=request)

    with pytest.raises(expected):
        run(handler)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"model": "wrong", "embeddings": [[1, 0], [0, 1]]},
        {"model": "bge-m3", "embeddings": []},
        {"model": "bge-m3", "embeddings": [[1, 0]]},
        {"model": "bge-m3", "embeddings": [[1, 0], [1]]},
        {"model": "bge-m3", "embeddings": [[1, 0], [0, 0]]},
        {"model": "bge-m3", "embeddings": [[1, 0], ["bad", 1]]},
    ],
)
def test_rejects_invalid_response_and_batch_shape(payload: dict) -> None:
    with pytest.raises(InvalidModelResponseError):
        run(lambda request: httpx2.Response(200, json=payload))


def test_rejects_non_json_response() -> None:
    with pytest.raises(InvalidModelResponseError):
        run(lambda request: httpx2.Response(200, text="not JSON"))


def test_rejects_nonfinite_numbers_in_http_response() -> None:
    with pytest.raises(InvalidModelResponseError):
        run(
            lambda request: httpx2.Response(
                200, text='{"model":"bge-m3","embeddings":[[1,0],[NaN,1]]}'
            )
        )


@pytest.mark.parametrize(
    "url",
    [
        "not-a-url",
        "ftp://localhost",
        "http://user:password@localhost",
        "http://localhost?key=value",
        "http://localhost#fragment",
    ],
)
def test_rejects_invalid_base_url(url: str) -> None:
    with pytest.raises(ValueError):
        OllamaEmbeddingModel(
            base_url=url, model_name="bge-m3", expected_dimension=1024, timeout_seconds=30
        )


@pytest.mark.parametrize("name", [None, "", " "])
def test_rejects_unconfigured_model(name: str | None) -> None:
    with pytest.raises(ModelNotConfiguredError):
        OllamaEmbeddingModel(
            base_url="http://localhost:11434",
            model_name=name,
            expected_dimension=1024,
            timeout_seconds=30,
        )


@pytest.mark.parametrize("timeout,dimension", [(0, 2), (float("inf"), 2), (1, 0), (1, -1)])
def test_rejects_invalid_limits(timeout: float, dimension: int) -> None:
    with pytest.raises(ValueError):
        OllamaEmbeddingModel(
            base_url="http://localhost:11434",
            model_name="bge-m3",
            expected_dimension=dimension,
            timeout_seconds=timeout,
        )


@pytest.mark.parametrize("num_gpu", [-1, 1.5, True])
def test_rejects_invalid_num_gpu(num_gpu: object) -> None:
    with pytest.raises(ValueError):
        OllamaEmbeddingModel(
            base_url="http://localhost:11434",
            model_name="bge-m3",
            expected_dimension=1024,
            timeout_seconds=30,
            num_gpu=num_gpu,  # type: ignore[arg-type]
        )


def test_closes_owned_client(monkeypatch: pytest.MonkeyPatch) -> None:
    async def call() -> None:
        client = httpx2.AsyncClient()
        monkeypatch.setattr(httpx2, "AsyncClient", lambda: client)
        model = OllamaEmbeddingModel(
            base_url="http://localhost:11434",
            model_name="bge-m3",
            expected_dimension=1024,
            timeout_seconds=30,
        )
        await model.aclose()
        assert client.is_closed

    asyncio.run(call())
