
import httpx2
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers.vector_store_errors import VectorStoreConnectionError
from app.schemas.retrieval import RetrievedSource
from app.schemas.vector_store import VectorRecord


class TrackingVectorStore:
    def __init__(self) -> None:
        self.closed = False

    async def upsert(self, records: list[VectorRecord]) -> None:
        pass

    async def search(self, query_vector: list[float], *, k: int) -> list[RetrievedSource]:
        return []

    async def delete(self, chunk_ids: list[str]) -> None:
        pass

    async def aclose(self) -> None:
        self.closed = True


def test_lifespan_exposes_ready_vector_store_and_closes_it() -> None:
    store = TrackingVectorStore()
    received_settings: list[Settings] = []

    async def factory(settings: Settings) -> TrackingVectorStore:
        received_settings.append(settings)
        return store

    settings = Settings(_env_file=None, ollama_chat_model=None)
    application = create_app(settings=settings, vector_store_factory=factory)

    assert not hasattr(application.state, "vector_store")
    with TestClient(application):
        assert application.state.vector_store is store
        assert application.state.vector_store_provider_status == "ready"
        assert not store.closed

    assert received_settings == [settings]
    assert store.closed


def test_vector_store_startup_failure_prevents_app_start_and_closes_http_client() -> None:
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(lambda request: None))

    async def failing_factory(settings: Settings) -> TrackingVectorStore:
        raise VectorStoreConnectionError(
            "unavailable",
            operation="collection_exists",
            collection="vehicle_knowledge_v1",
        )

    application = create_app(
        settings=Settings(_env_file=None, ollama_chat_model=None),
        client_factory=lambda: client,
        vector_store_factory=failing_factory,
    )

    with pytest.raises(VectorStoreConnectionError), TestClient(application):
        pytest.fail("application must not start without its configured vector store")

    assert client.is_closed
