import pytest
from pydantic import ValidationError

from app.core.config import (
    Environment,
    RerankerProvider,
    Settings,
    VectorStoreProvider,
    get_settings,
)


def test_settings_have_safe_local_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment is Environment.DEVELOPMENT
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert str(settings.ollama_base_url) == "http://127.0.0.1:11434/"
    assert settings.ollama_chat_model is None
    assert settings.ollama_embedding_num_gpu is None
    assert settings.model_timeout_seconds == 30
    assert settings.model_max_output_tokens == 512
    assert settings.model_max_attempts == 3
    assert settings.model_retry_base_delay_seconds == 0.1
    assert settings.api_key is None
    assert settings.vector_store_provider is VectorStoreProvider.MEMORY
    assert settings.embedding_dimension == 1024
    assert str(settings.qdrant_url) == "http://127.0.0.1:6333/"
    assert settings.qdrant_collection_name == "vehicle_knowledge_v1"
    assert settings.qdrant_timeout_seconds == 10
    assert settings.qdrant_api_key is None
    assert settings.reranker_provider is RerankerProvider.PASS_THROUGH
    assert settings.reranker_model == "BAAI/bge-reranker-base"
    assert settings.reranker_batch_size == 8


def test_settings_read_prefixed_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VEHICLE_AGENT_ENVIRONMENT", "production")
    monkeypatch.setenv("VEHICLE_AGENT_PORT", "9000")
    monkeypatch.setenv("VEHICLE_AGENT_API_KEY", "do-not-log-this-key")
    monkeypatch.setenv("VEHICLE_AGENT_OLLAMA_BASE_URL", "http://ollama:11434")
    monkeypatch.setenv("VEHICLE_AGENT_OLLAMA_CHAT_MODEL", "qwen3:8b")
    monkeypatch.setenv("VEHICLE_AGENT_OLLAMA_EMBEDDING_NUM_GPU", "0")
    monkeypatch.setenv("VEHICLE_AGENT_MODEL_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("VEHICLE_AGENT_MODEL_MAX_OUTPUT_TOKENS", "2048")
    monkeypatch.setenv("VEHICLE_AGENT_VECTOR_STORE_PROVIDER", "qdrant")
    monkeypatch.setenv("VEHICLE_AGENT_EMBEDDING_DIMENSION", "768")
    monkeypatch.setenv("VEHICLE_AGENT_QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("VEHICLE_AGENT_QDRANT_COLLECTION_NAME", "vehicle_docs_v2")
    monkeypatch.setenv("VEHICLE_AGENT_QDRANT_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("VEHICLE_AGENT_QDRANT_API_KEY", "qdrant-secret")
    monkeypatch.setenv("VEHICLE_AGENT_RERANKER_PROVIDER", "fastembed")
    monkeypatch.setenv("VEHICLE_AGENT_RERANKER_BATCH_SIZE", "4")

    settings = Settings(_env_file=None)

    assert settings.environment is Environment.PRODUCTION
    assert settings.port == 9000
    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == "do-not-log-this-key"
    assert str(settings.ollama_base_url) == "http://ollama:11434/"
    assert settings.ollama_chat_model == "qwen3:8b"
    assert settings.ollama_embedding_num_gpu == 0
    assert settings.model_timeout_seconds == 45
    assert settings.model_max_output_tokens == 2048
    assert settings.vector_store_provider is VectorStoreProvider.QDRANT
    assert settings.embedding_dimension == 768
    assert str(settings.qdrant_url) == "http://qdrant:6333/"
    assert settings.qdrant_collection_name == "vehicle_docs_v2"
    assert settings.qdrant_timeout_seconds == 15
    assert settings.qdrant_api_key is not None
    assert settings.qdrant_api_key.get_secret_value() == "qdrant-secret"
    assert settings.reranker_provider is RerankerProvider.FASTEMBED
    assert settings.reranker_batch_size == 4


@pytest.mark.parametrize("budget", [0, 8193])
def test_settings_reject_invalid_output_budget(budget: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, model_max_output_tokens=budget)


def test_settings_do_not_expose_api_key_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VEHICLE_AGENT_API_KEY", "do-not-log-this-key")
    monkeypatch.setenv("VEHICLE_AGENT_QDRANT_API_KEY", "do-not-log-qdrant-key")

    settings = Settings(_env_file=None)

    assert "do-not-log-this-key" not in repr(settings)
    assert "do-not-log-qdrant-key" not in repr(settings)


@pytest.mark.parametrize("port", [0, 65536])
def test_settings_reject_invalid_port(port: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, port=port)


def test_settings_reject_non_positive_model_timeout() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, model_timeout_seconds=0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("embedding_dimension", 0),
        ("qdrant_timeout_seconds", 0),
        ("qdrant_timeout_seconds", float("inf")),
        ("qdrant_collection_name", " "),
        ("qdrant_collection_name", "invalid/name"),
    ],
)
def test_settings_reject_invalid_vector_store_configuration(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


@pytest.mark.parametrize(
    ("max_attempts", "base_delay_seconds"),
    [(0, 0.1), (6, 0.1), (3, -0.1)],
)
def test_settings_reject_unsafe_retry_policy(
    max_attempts: int,
    base_delay_seconds: float,
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            model_max_attempts=max_attempts,
            model_retry_base_delay_seconds=base_delay_seconds,
        )


def test_get_settings_reuses_one_instance_per_process() -> None:
    get_settings.cache_clear()

    first = get_settings()
    second = get_settings()

    assert first is second
    get_settings.cache_clear()
