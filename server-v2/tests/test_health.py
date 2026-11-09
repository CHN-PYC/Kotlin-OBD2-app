import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError

from app.core.config import Settings
from app.main import create_app
from app.providers.qdrant_vector_store import QdrantVectorStore
from app.providers.vector_store_errors import VectorStoreConfigurationError
from app.schemas.retrieval import RetrievedSource
from app.schemas.vector_store import VectorRecord
from app.services.memory.errors import SessionMemoryError
from app.services.memory.redis_store import RedisSessionMemoryStore


class StubVectorStore:
    """Vector store without ping: readiness must report not_probed."""

    async def upsert(self, records: list[VectorRecord]) -> None:
        pass

    async def search(self, query_vector: list[float], *, k: int) -> list[RetrievedSource]:
        return []

    async def delete(self, chunk_ids: list[str]) -> None:
        pass

    async def aclose(self) -> None:
        pass


class FailingPingVectorStore(StubVectorStore):
    async def ping(self) -> None:
        raise RuntimeError("secret qdrant detail")


class HangingPingVectorStore(StubVectorStore):
    async def ping(self) -> None:
        await asyncio.Event().wait()


def _client_with(store: StubVectorStore, **settings: object) -> TestClient:
    async def factory(_: Settings) -> StubVectorStore:
        return store

    app = create_app(
        settings=Settings(_env_file=None, ollama_chat_model=None, **settings),  # type: ignore[arg-type]
        vector_store_factory=factory,  # type: ignore[arg-type]
    )
    return TestClient(app)


def test_ready_reports_all_components_with_default_settings() -> None:
    app = create_app(settings=Settings(_env_file=None, ollama_chat_model=None))
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "components": {
            "session_memory": "ok",
            "vector_store": "ok",
            "chat_model": "not_configured",
            "embedding_model": "not_configured",
        },
    }


def test_failing_probe_reports_degraded_without_leaking_error() -> None:
    with _client_with(FailingPingVectorStore()) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["components"]["vector_store"] == "unavailable"
    assert "secret" not in response.text


def test_hanging_probe_is_bounded_by_timeout() -> None:
    with _client_with(HangingPingVectorStore(), health_probe_timeout_seconds=0.05) as client:
        response = client.get("/health/ready")

    assert response.json()["components"]["vector_store"] == "unavailable"


def test_component_without_ping_is_not_probed() -> None:
    with _client_with(StubVectorStore()) as client:
        response = client.get("/health/ready")

    assert response.json()["status"] == "ready"
    assert response.json()["components"]["vector_store"] == "not_probed"


def test_liveness_does_not_touch_dependencies() -> None:
    with _client_with(FailingPingVectorStore()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_redis_ping_failure_maps_to_session_memory_error() -> None:
    client = Mock()
    client.ping = AsyncMock(side_effect=ConnectionError("down"))
    store = RedisSessionMemoryStore(
        url="redis://localhost",
        ttl_seconds=1800,
        max_turns=10,
        client=client,  # type: ignore[arg-type]
    )

    with pytest.raises(SessionMemoryError):
        asyncio.run(store.ping())


def test_qdrant_ping_rejects_missing_collection() -> None:
    client = Mock()
    client.collection_exists = AsyncMock(return_value=False)
    store = QdrantVectorStore(
        url="http://localhost:6333",
        collection_name="vehicle_knowledge_test",
        dimension=2,
        timeout_seconds=10,
        client=client,  # type: ignore[arg-type]
    )

    with pytest.raises(VectorStoreConfigurationError):
        asyncio.run(store.ping())
