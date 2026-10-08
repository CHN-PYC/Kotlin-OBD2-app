import math
from collections.abc import Awaitable
from typing import TypeVar
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx
from pydantic import ValidationError
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import (
    ApiException,
    ResponseHandlingException,
    UnexpectedResponse,
)
from qdrant_client.models import Distance, PointIdsList, PointStruct, VectorParams

from app.contracts.vector_store import VectorStore
from app.providers.vector_store_errors import (
    VectorStoreAuthenticationError,
    VectorStoreConfigurationError,
    VectorStoreConnectionError,
    VectorStoreInvalidResponseError,
    VectorStoreProviderError,
    VectorStoreRateLimitError,
    VectorStoreRequestError,
    VectorStoreServerError,
    VectorStoreTimeoutError,
)
from app.schemas.knowledge import KnowledgeChunk
from app.schemas.retrieval import RetrievedSource
from app.schemas.vector_store import VectorRecord

ResultT = TypeVar("ResultT")


class QdrantCollectionConfigurationError(VectorStoreConfigurationError):
    """The existing collection cannot store vectors produced by this application."""


class QdrantPayloadError(VectorStoreInvalidResponseError):
    """A stored point cannot be converted back to an application knowledge chunk."""


def _point_id(chunk_id: str) -> UUID:
    # LEARNING: UUID5 is deterministic. The same chunk_id overwrites the same point,
    # which makes ingestion idempotent instead of creating duplicates on every run.
    return uuid5(NAMESPACE_URL, f"vehicle-agent/chunk/{chunk_id}")


class QdrantVectorStore(VectorStore):
    """Qdrant adapter; collection initialization is explicit and asynchronous."""

    def __init__(
        self,
        *,
        url: str,
        collection_name: str,
        dimension: int,
        timeout_seconds: int,
        api_key: str | None = None,
        client: AsyncQdrantClient | None = None,
    ) -> None:
        if type(dimension) is not int or dimension <= 0:
            raise ValueError("dimension must be a positive integer")
        if type(timeout_seconds) is not int or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive integer")
        if not collection_name.strip():
            raise ValueError("collection_name must not be blank")

        self._collection_name = collection_name
        self._dimension = dimension
        self._owns_client = client is None
        self._client = (
            client
            if client is not None
            else AsyncQdrantClient(url=url, api_key=api_key, timeout=timeout_seconds)
        )

    async def ensure_collection(self) -> None:
        exists = await self._request(
            "collection_exists",
            self._client.collection_exists(self._collection_name),
        )
        if not exists:
            # LEARNING: COSINE matches the retrieval score semantics used by the gate.
            # Changing the embedding model/dimension requires a versioned collection.
            created = await self._request(
                "create_collection",
                self._client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=VectorParams(size=self._dimension, distance=Distance.COSINE),
                ),
            )
            if not created:
                raise VectorStoreInvalidResponseError(
                    "Qdrant did not confirm collection creation",
                    operation="create_collection",
                    collection=self._collection_name,
                )
            return

        info = await self._request(
            "get_collection",
            self._client.get_collection(self._collection_name),
        )
        vectors = info.config.params.vectors
        if not isinstance(vectors, VectorParams):
            raise QdrantCollectionConfigurationError(
                "collection must contain one unnamed dense vector",
                operation="get_collection",
                collection=self._collection_name,
            )
        if vectors.size != self._dimension or vectors.distance is not Distance.COSINE:
            raise QdrantCollectionConfigurationError(
                "collection vector configuration does not match application settings",
                operation="get_collection",
                collection=self._collection_name,
            )

    async def upsert(self, records: list[VectorRecord]) -> None:
        points: list[PointStruct] = []
        seen_ids: set[str] = set()
        for record in records:
            chunk_id = record.chunk.chunk_id
            if chunk_id in seen_ids:
                raise ValueError("upsert batch must not contain duplicate chunk IDs")
            seen_ids.add(chunk_id)
            self._validate_vector(record.vector)
            points.append(
                PointStruct(
                    id=_point_id(chunk_id),
                    vector=record.vector,
                    payload=record.chunk.model_dump(mode="json"),
                )
            )

        if points:
            await self._request(
                "upsert",
                self._client.upsert(
                    collection_name=self._collection_name,
                    points=points,
                    wait=True,
                ),
            )

    async def search(self, query_vector: list[float], *, k: int) -> list[RetrievedSource]:
        if type(k) is not int or k <= 0:
            raise ValueError("k must be a positive integer")
        self._validate_vector(query_vector)
        response = await self._request(
            "search",
            self._client.query_points(
                collection_name=self._collection_name,
                query=query_vector,
                limit=k,
                with_payload=True,
                with_vectors=False,
            ),
        )

        sources: list[RetrievedSource] = []
        seen_ids: set[str] = set()
        for point in response.points:
            try:
                chunk = KnowledgeChunk.model_validate(point.payload)
            except (TypeError, ValidationError) as exc:
                raise QdrantPayloadError(
                    "search result contains invalid chunk payload",
                    operation="search",
                    collection=self._collection_name,
                ) from exc
            if chunk.chunk_id in seen_ids:
                raise QdrantPayloadError(
                    "search result contains duplicate chunk IDs",
                    operation="search",
                    collection=self._collection_name,
                )
            if str(point.id) != str(_point_id(chunk.chunk_id)):
                raise QdrantPayloadError(
                    "point ID does not match payload chunk_id",
                    operation="search",
                    collection=self._collection_name,
                )
            seen_ids.add(chunk.chunk_id)
            sources.append(
                RetrievedSource(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    title=chunk.title,
                    source_url=chunk.source_url,
                    score=float(point.score),
                    text=chunk.text,
                    topic=chunk.topic,
                    pid_tags=chunk.pid_tags,
                    section_title=chunk.section_title,
                )
            )
        return sources

    async def delete(self, chunk_ids: list[str]) -> None:
        if any(type(chunk_id) is not str or not chunk_id.strip() for chunk_id in chunk_ids):
            raise ValueError("chunk IDs must be non-blank strings")
        unique_ids = list(dict.fromkeys(chunk_ids))
        if unique_ids:
            await self._request(
                "delete",
                self._client.delete(
                    collection_name=self._collection_name,
                    points_selector=PointIdsList(points=[_point_id(item) for item in unique_ids]),
                    wait=True,
                ),
            )

    def _validate_vector(self, vector: list[float]) -> None:
        if len(vector) != self._dimension:
            raise ValueError(f"vector dimension must be {self._dimension}")
        if not all(math.isfinite(value) for value in vector):
            raise ValueError("vector values must be finite")
        if not any(value != 0.0 for value in vector):
            raise ValueError("vector must not be all zero")

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.close()

    async def _request(self, operation: str, request: Awaitable[ResultT]) -> ResultT:
        try:
            return await request
        except ApiException as exc:
            raise self._map_error(exc, operation=operation) from exc

    def _map_error(self, exc: ApiException, *, operation: str) -> VectorStoreProviderError:
        error_type: type[VectorStoreProviderError]
        message: str
        if isinstance(exc, UnexpectedResponse):
            status = exc.status_code
            if status in {401, 403}:
                error_type = VectorStoreAuthenticationError
            elif status == 429:
                error_type = VectorStoreRateLimitError
            elif status is not None and status >= 500:
                error_type = VectorStoreServerError
            else:
                error_type = VectorStoreRequestError
            message = f"Qdrant returned HTTP {status or 'unknown'}"
        elif isinstance(exc, ResponseHandlingException):
            if isinstance(exc.source, httpx.TimeoutException):
                error_type = VectorStoreTimeoutError
                message = "Qdrant request timed out"
            elif isinstance(exc.source, httpx.TransportError):
                error_type = VectorStoreConnectionError
                message = "Qdrant connection failed"
            else:
                error_type = VectorStoreInvalidResponseError
                message = "Qdrant returned an unreadable response"
        else:
            error_type = VectorStoreConnectionError
            message = "Qdrant request failed"
        return error_type(message, operation=operation, collection=self._collection_name)
