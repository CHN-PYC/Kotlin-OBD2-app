import asyncio

import httpx2
import pytest

from app.core.config import Settings
from app.providers.chat import ChatMessage, ChatModel, ChatRequest
from app.providers.circuit_breaker import CircuitOpenError
from app.providers.errors import ModelNotConfiguredError, ModelServerError
from app.providers.factory import create_chat_model


def _success_response() -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "model": "qwen3:4b",
            "message": {"role": "assistant", "content": "grounded answer"},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 12,
            "eval_count": 3,
        },
    )


def test_factory_builds_working_chat_model_from_settings() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return _success_response()

    async def run() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            settings = Settings(_env_file=None, ollama_chat_model="qwen3:4b")
            model = create_chat_model(settings, client=client)
            result = await model.generate(
                ChatRequest(messages=[ChatMessage(role="user", content="question")])
            )

            assert isinstance(model, ChatModel)
            assert model.provider_name == "ollama"
            assert model.model_name == "qwen3:4b"
            assert result.content == "grounded answer"

    asyncio.run(run())


def test_factory_applies_retry_policy_from_settings() -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx2.Response(503, json={"error": "temporarily unavailable"})
        return _success_response()

    async def run() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            settings = Settings(
                _env_file=None,
                ollama_chat_model="qwen3:4b",
                model_max_attempts=2,
                model_retry_base_delay_seconds=0,
            )
            model = create_chat_model(settings, client=client)
            result = await model.generate(
                ChatRequest(messages=[ChatMessage(role="user", content="question")])
            )

            assert result.content == "grounded answer"

    asyncio.run(run())
    assert calls == 2


def test_factory_fails_fast_when_chat_model_is_not_configured() -> None:
    settings = Settings(_env_file=None, ollama_chat_model=None)

    with pytest.raises(ModelNotConfiguredError):
        create_chat_model(settings)


def test_factory_counts_exhausted_requests_not_individual_retries() -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(503)

    async def run() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            model = create_chat_model(
                Settings(
                    _env_file=None,
                    ollama_chat_model="qwen3:4b",
                    model_max_attempts=2,
                    model_retry_base_delay_seconds=0,
                    model_circuit_failure_threshold=2,
                ),
                client=client,
            )
            request = ChatRequest(messages=[ChatMessage(role="user", content="question")])
            for _ in range(2):
                with pytest.raises(ModelServerError):
                    await model.generate(request)
            with pytest.raises(CircuitOpenError):
                await model.generate(request)

    asyncio.run(run())
    assert calls == 4
