import pytest

from app.providers.errors import (
    InvalidModelResponseError,
    ModelConnectionError,
    ModelNotConfiguredError,
    ModelProviderError,
    ModelRequestError,
    ModelServerError,
    ModelTimeoutError,
)


@pytest.mark.parametrize(
    ("error_type", "expected_code", "expected_retryable"),
    [
        (ModelNotConfiguredError, "not_configured", False),
        (ModelTimeoutError, "timeout", True),
        (ModelConnectionError, "connection_error", True),
        (ModelRequestError, "request_error", False),
        (ModelServerError, "server_error", True),
        (InvalidModelResponseError, "invalid_response", False),
    ],
)
def test_model_errors_expose_stable_retry_metadata(
    error_type: type[ModelProviderError],
    expected_code: str,
    expected_retryable: bool,
) -> None:
    error = error_type(
        "provider operation failed",
        provider="ollama",
        model="qwen3:8b",
    )

    assert error.code == expected_code
    assert error.retryable is expected_retryable
    assert error.provider == "ollama"
    assert error.model == "qwen3:8b"


def test_model_error_is_catchable_through_base_type() -> None:
    error = ModelTimeoutError(
        "request exceeded 30 seconds",
        provider="ollama",
        model="qwen3:8b",
    )

    with pytest.raises(ModelProviderError) as captured:
        raise error

    assert captured.value is error


def test_model_error_string_contains_debugging_identity() -> None:
    error = ModelConnectionError(
        "connection refused",
        provider="ollama",
        model="qwen3:8b",
    )

    rendered = str(error)

    assert "connection_error" in rendered
    assert "ollama" in rendered
    assert "qwen3:8b" in rendered
    assert "connection refused" in rendered


def test_model_error_allows_missing_model_for_configuration_failure() -> None:
    error = ModelNotConfiguredError(
        "chat model is not configured",
        provider="ollama",
    )

    assert error.model is None
    assert "unconfigured" in str(error)


def test_model_error_does_not_store_prompt_or_raw_response() -> None:
    error = InvalidModelResponseError(
        "response content was empty",
        provider="ollama",
        model="qwen3:8b",
    )

    assert not hasattr(error, "prompt")
    assert not hasattr(error, "raw_response")
