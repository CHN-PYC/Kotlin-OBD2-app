import asyncio

import httpx
import pytest
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from app.providers.qdrant_vector_store import QdrantVectorStore
from app.providers.vector_store_errors import (
    VectorStoreAuthenticationError,
    VectorStoreConnectionError,
    VectorStoreInvalidResponseError,
    VectorStoreProviderError,
    VectorStoreRateLimitError,
    VectorStoreRequestError,
    VectorStoreServerError,
    VectorStoreTimeoutError,
)


class FailingQdrantClient:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def collection_exists(self, collection_name: str) -> bool:
        raise self.error


def store(client: FailingQdrantClient) -> QdrantVectorStore:
    return QdrantVectorStore(
        url="http://localhost:6333",
        collection_name="vehicle_knowledge_test",
        dimension=2,
        timeout_seconds=10,
        client=client,  # type: ignore[arg-type]
    )


def http_error(status: int) -> UnexpectedResponse:
    return UnexpectedResponse(status, "test", b"provider details", httpx.Headers())


@pytest.mark.parametrize(
    ("error", "expected_type", "retryable"),
    [
        (ResponseHandlingException(httpx.ReadTimeout("slow")), VectorStoreTimeoutError, True),
        (
            ResponseHandlingException(httpx.ConnectError("down")),
            VectorStoreConnectionError,
            True,
        ),
        (http_error(401), VectorStoreAuthenticationError, False),
        (http_error(429), VectorStoreRateLimitError, True),
        (http_error(503), VectorStoreServerError, True),
        (http_error(400), VectorStoreRequestError, False),
        (ResponseHandlingException(ValueError("bad JSON")), VectorStoreInvalidResponseError, False),
    ],
)
def test_maps_sdk_errors_to_stable_application_errors(
    error: Exception,
    expected_type: type[VectorStoreProviderError],
    retryable: bool,
) -> None:
    with pytest.raises(expected_type) as captured:
        asyncio.run(store(FailingQdrantClient(error)).ensure_collection())

    assert captured.value.retryable is retryable
    assert captured.value.operation == "collection_exists"
    assert captured.value.collection == "vehicle_knowledge_test"
    assert "provider details" not in str(captured.value)
