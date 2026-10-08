import httpx2
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers.chat import ChatModel


def test_lifespan_creates_shared_chat_model_and_closes_client() -> None:
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(lambda request: None))
    settings = Settings(_env_file=None, ollama_chat_model="qwen3:4b")
    application = create_app(settings=settings, client_factory=lambda: client)

    assert not client.is_closed

    with TestClient(application):
        assert application.state.http_client is client
        assert isinstance(application.state.chat_model, ChatModel)
        assert application.state.model_provider_status == "ready"
        assert not client.is_closed

    assert client.is_closed


def test_lifespan_keeps_fallback_available_when_model_is_not_configured() -> None:
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(lambda request: None))
    settings = Settings(_env_file=None, ollama_chat_model=None)
    application = create_app(settings=settings, client_factory=lambda: client)

    with TestClient(application) as test_client:
        response = test_client.get("/health")

        assert response.status_code == 200
        assert application.state.chat_model is None
        assert application.state.model_provider_status == "not_configured"

    assert client.is_closed


def test_lifespan_creates_resources_only_after_startup() -> None:
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(lambda request: None))
    settings = Settings(_env_file=None, ollama_chat_model="qwen3:4b")
    application = create_app(settings=settings, client_factory=lambda: client)

    assert not hasattr(application.state, "http_client")
    assert not hasattr(application.state, "chat_model")

    with TestClient(application):
        assert application.state.http_client is client
        assert application.state.chat_model is not None
