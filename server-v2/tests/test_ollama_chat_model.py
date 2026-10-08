import asyncio
import json

import httpx2
import pytest

from app.providers.chat import ChatMessage, ChatOptions, ChatRequest, ChatResult
from app.providers.errors import (
    InvalidModelResponseError,
    ModelConnectionError,
    ModelNotConfiguredError,
    ModelRequestError,
    ModelServerError,
    ModelTimeoutError,
)
from app.providers.ollama import OllamaChatModel


def _chat_request() -> ChatRequest:
    return ChatRequest(
        messages=[
            ChatMessage(role="system", content="Use grounded evidence."),
            ChatMessage(role="user", content="Why is coolant temperature high?"),
        ],
        options=ChatOptions(temperature=0.2, max_output_tokens=256),
    )


def _run_model(handler: httpx2.MockTransport) -> ChatResult:
    async def run() -> ChatResult:
        async with httpx2.AsyncClient(transport=handler) as client:
            model = OllamaChatModel(
                base_url="http://ollama:11434",
                model_name="qwen3:8b",
                timeout_seconds=30,
                client=client,
            )
            return await model.generate(_chat_request())

    return asyncio.run(run())


def test_ollama_chat_model_maps_request_and_response() -> None:
    captured_payload: dict = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured_payload.update(json.loads(request.content))
        assert request.url.path == "/api/chat"
        return httpx2.Response(
            200,
            json={
                "model": "qwen3:8b",
                "message": {"role": "assistant", "content": "Check coolant and fan."},
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 42,
                "eval_count": 8,
            },
        )

    result = _run_model(httpx2.MockTransport(handler))

    assert captured_payload == {
        "model": "qwen3:8b",
        "messages": [
            {"role": "system", "content": "Use grounded evidence."},
            {"role": "user", "content": "Why is coolant temperature high?"},
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.2, "num_predict": 256},
    }
    assert result.content == "Check coolant and fan."
    assert result.provider == "ollama"
    assert result.model == "qwen3:8b"
    assert result.finish_reason == "stop"
    assert result.input_tokens == 42
    assert result.output_tokens == 8


def test_ollama_chat_model_rejects_missing_model_configuration() -> None:
    with pytest.raises(ModelNotConfiguredError):
        OllamaChatModel(
            base_url="http://ollama:11434",
            model_name=None,
            timeout_seconds=30,
        )


def test_ollama_chat_model_maps_timeout() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("slow model", request=request)

    with pytest.raises(ModelTimeoutError):
        _run_model(httpx2.MockTransport(handler))


def test_ollama_chat_model_maps_connection_failure() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection refused", request=request)

    with pytest.raises(ModelConnectionError):
        _run_model(httpx2.MockTransport(handler))


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [(400, ModelRequestError), (503, ModelServerError)],
)
def test_ollama_chat_model_classifies_http_status(
    status_code: int,
    expected_error: type[Exception],
) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status_code, json={"error": "provider failed"})

    with pytest.raises(expected_error):
        _run_model(httpx2.MockTransport(handler))


def test_ollama_chat_model_rejects_invalid_success_payload() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={
                "model": "qwen3:8b",
                "message": {"role": "assistant", "content": "   "},
                "done": True,
            },
        )

    with pytest.raises(InvalidModelResponseError):
        _run_model(httpx2.MockTransport(handler))
