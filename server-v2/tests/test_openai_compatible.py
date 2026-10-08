import asyncio
import json
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.main import create_app
from app.providers.chat import ChatMessage, ChatRequest
from app.providers.errors import (
    InvalidModelResponseError,
    ModelConnectionError,
    ModelNotConfiguredError,
    ModelRateLimitError,
    ModelRequestError,
    ModelServerError,
    ModelTimeoutError,
)
from app.providers.factory import create_chat_model
from app.providers.openai_compatible import OpenAICompatibleChatModel


def completion(finish: str = "stop") -> dict:
    return {
        "model": "remote-chat",
        "choices": [
            {
                "message": {"role": "assistant", "content": '{"answer":"Check cooling."}'},
                "finish_reason": finish,
            }
        ],
        "usage": {"prompt_tokens": 30, "completion_tokens": 8},
    }


def config(**changes) -> Settings:
    values = {
        "model_provider": "openai_compatible",
        "llm_base_url": "https://remote.test/v1/",
        "llm_model": "remote-chat",
        "llm_api_key": "test-only-key",
        "llm_json_mode": True,
        "model_retry_base_delay_seconds": 0,
        "model_max_attempts": 2,
    }
    values.update(changes)
    return Settings(_env_file=None, **values)


def request() -> ChatRequest:
    return ChatRequest(messages=[ChatMessage(role="user", content="Return JSON.")])


def adapter(client=None, **changes) -> OpenAICompatibleChatModel:
    values = {
        "base_url": "https://remote.test/v1/",
        "model_name": "remote-chat",
        "api_key": SecretStr("test-only-key"),
        "timeout_seconds": 10,
        "client": client,
    }
    values.update(changes)
    return OpenAICompatibleChatModel(**values)


def test_factory_maps_request_auth_response_and_json_mode() -> None:
    def handler(req: httpx2.Request) -> httpx2.Response:
        assert str(req.url) == "https://remote.test/v1/chat/completions"
        assert req.headers["Authorization"] == "Bearer test-only-key"
        body = json.loads(req.content)
        assert body["model"] == "remote-chat"
        assert body["max_tokens"] == 512
        assert body["temperature"] == 0
        assert body["stream"] is False
        assert body["messages"] == [{"role": "user", "content": "Return JSON."}]
        assert body["response_format"] == {"type": "json_object"}
        return httpx2.Response(200, json=completion())

    async def run() -> None:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            result = await create_chat_model(config(), client=client).generate(request())
            assert result.provider == "openai_compatible"
            assert result.input_tokens == 30
            assert result.output_tokens == 8
            assert result.finish_reason == "stop"

    asyncio.run(run())


@pytest.mark.parametrize(
    "status,error,count",
    [
        (400, ModelRequestError, 1),
        (401, ModelRequestError, 1),
        (403, ModelRequestError, 1),
        (429, ModelRateLimitError, 2),
        (500, ModelServerError, 2),
        (503, ModelServerError, 2),
    ],
)
def test_factory_retries_only_transient_statuses(status, error, count) -> None:
    calls = []

    def handler(req):
        calls.append(req)
        return httpx2.Response(status, json={"error": "test-only-key must not be exposed"})

    async def run():
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            with pytest.raises(error) as caught:
                await create_chat_model(config(), client=client).generate(request())
            assert "test-only-key" not in str(caught.value)

    asyncio.run(run())
    assert len(calls) == count


@pytest.mark.parametrize(
    "cause,error",
    [(httpx2.ReadTimeout, ModelTimeoutError), (httpx2.ConnectError, ModelConnectionError)],
)
def test_network_errors_are_normalized(cause, error) -> None:
    def handler(req):
        raise cause("network failure", request=req)

    async def run():
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            with pytest.raises(error):
                await adapter(client).generate(request())

    asyncio.run(run())


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"model": "remote", "choices": []},
        {
            "model": "remote",
            "choices": [
                {"message": {"role": "assistant", "content": None}, "finish_reason": "stop"}
            ],
        },
        {
            "model": "remote",
            "choices": [
                {"message": {"role": "assistant", "content": " "}, "finish_reason": "stop"}
            ],
        },
    ],
)
def test_invalid_completions_are_rejected(data) -> None:
    async def run():
        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(lambda req: httpx2.Response(200, json=data))
        ) as client:
            with pytest.raises(InvalidModelResponseError):
                await adapter(client).generate(request())

    asyncio.run(run())


def test_plain_mode_usage_absence_and_external_client_ownership() -> None:
    def handler(req):
        assert "response_format" not in json.loads(req.content)
        data = completion("length")
        del data["usage"]
        return httpx2.Response(200, json=data)

    async def run():
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
            model = adapter(client)
            result = await model.generate(request())
            assert result.finish_reason == "length"
            assert result.input_tokens == 0
            await model.aclose()
            assert not client.is_closed

    asyncio.run(run())


@pytest.mark.parametrize("field", ["base_url", "model_name", "api_key"])
def test_missing_remote_settings_fail_before_client_creation(field) -> None:
    with pytest.raises(ModelNotConfiguredError):
        adapter(**{field: None})


def test_config_rejects_unknown_provider() -> None:
    with pytest.raises(ValidationError):
        config(model_provider="typo")


@pytest.mark.parametrize(
    "finish,mode,last",
    [
        ("stop", "llm_only", "build_response"),
        ("length", "llm_call_failed", "rule_fallback"),
    ],
)
def test_api_uses_remote_provider_through_workflow(finish, mode, last) -> None:
    outbound = httpx2.AsyncClient(
        transport=httpx2.MockTransport(lambda req: httpx2.Response(200, json=completion(finish)))
    )
    app = create_app(settings=config(), client_factory=lambda: outbound)
    path = Path(__file__).parent / "fixtures/vehicle_qa_request.json"
    with TestClient(app) as client:
        response = client.post("/qa/vehicle", json=json.loads(path.read_text(encoding="utf-8")))
        assert app.state.model_provider_status == "ready"
    assert response.status_code == 200
    body = response.json()
    assert body["answer_mode"] == mode
    assert body["agent_trace"][0]["step"] == "prepare_baseline"
    assert body["agent_trace"][-1]["step"] == last
    assert outbound.is_closed


def test_missing_key_keeps_app_available_without_outbound_calls() -> None:
    def handler(req):
        raise AssertionError("must not make any remote request")

    outbound = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    app = create_app(settings=config(llm_api_key=None), client_factory=lambda: outbound)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert app.state.model_provider_status == "not_configured"
        assert app.state.chat_model is None
    assert outbound.is_closed


def test_malformed_http_body_becomes_invalid_response() -> None:
    async def run():
        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(lambda req: httpx2.Response(200, text="not JSON"))
        ) as client:
            with pytest.raises(InvalidModelResponseError):
                await adapter(client).generate(request())

    asyncio.run(run())


def test_owned_client_is_closed(monkeypatch) -> None:
    client = httpx2.AsyncClient()
    monkeypatch.setattr(httpx2, "AsyncClient", lambda: client)
    model = adapter()
    asyncio.run(model.aclose())
    assert client.is_closed


def test_environment_can_select_remote_without_exposing_key(monkeypatch) -> None:
    monkeypatch.setenv("VEHICLE_AGENT_MODEL_PROVIDER", "openai_compatible")
    monkeypatch.setenv("VEHICLE_AGENT_LLM_BASE_URL", "https://remote.test/v1")
    monkeypatch.setenv("VEHICLE_AGENT_LLM_MODEL", "remote-chat")
    monkeypatch.setenv("VEHICLE_AGENT_LLM_API_KEY", "private-test-key")
    settings = Settings(_env_file=None)
    assert settings.model_provider.value == "openai_compatible"
    assert settings.llm_api_key is not None
    assert settings.llm_api_key.get_secret_value() == "private-test-key"
    assert "private-test-key" not in repr(settings)
