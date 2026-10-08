import json
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"


def request_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_vehicle_qa_uses_llm_service_when_model_is_configured() -> None:
    outbound_requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        outbound_requests.append(request)
        return httpx2.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "answer": "Check the cooling system.",
                            "findings": ["Coolant temperature reached 108 C."],
                            "recommendations": ["Inspect the cooling fan."],
                        }
                    ),
                },
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 100,
                "eval_count": 8,
            },
        )

    outbound_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    settings = Settings(_env_file=None, ollama_chat_model="qwen3:4b")
    application = create_app(settings=settings, client_factory=lambda: outbound_client)

    with TestClient(application) as client:
        response = client.post("/qa/vehicle", json=request_payload())

    assert response.status_code == 200
    assert response.json()["answer"] == "Check the cooling system."
    assert response.json()["findings"] == ["Coolant temperature reached 108 C."]
    assert response.json()["answer_mode"] == "llm_only"
    assert [step["step"] for step in response.json()["agent_trace"]] == [
        "prepare_baseline",
        "query_rewrite",
        "prompt_build",
        "model_generation",
        "model_output_parse",
        "build_response",
    ]
    assert len(outbound_requests) == 1


def test_vehicle_qa_uses_rule_fallback_when_model_is_not_configured() -> None:
    outbound_requests: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        outbound_requests.append(request)
        return httpx2.Response(500)

    outbound_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    settings = Settings(_env_file=None, ollama_chat_model=None)
    application = create_app(settings=settings, client_factory=lambda: outbound_client)

    with TestClient(application) as client:
        response = client.post("/qa/vehicle", json=request_payload())

    assert response.status_code == 200
    assert response.json()["answer_mode"] == "rule_fallback"
    assert response.json()["confidence"] == "low"
    assert outbound_requests == []


@pytest.mark.parametrize("failure", ["timeout", "invalid_json", "length"])
def test_workflow_api_returns_rule_response_on_model_failure(failure: str) -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if failure == "timeout":
            raise httpx2.ReadTimeout("slow", request=request)
        return httpx2.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {
                    "role": "assistant",
                    "content": (
                        "not-json" if failure == "invalid_json" else '{"answer":"Partial answer"}'
                    ),
                },
                "done": True,
                "done_reason": "length" if failure == "length" else "stop",
            },
        )

    outbound = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    settings = Settings(
        _env_file=None,
        ollama_chat_model="qwen3:4b",
        model_max_attempts=2,
        model_retry_base_delay_seconds=0,
    )
    application = create_app(settings=settings, client_factory=lambda: outbound)
    payload = request_payload()
    with TestClient(application) as client:
        response = client.post("/qa/vehicle", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == payload["rule_summary"]["summary"]
    assert body["answer_mode"] == "llm_call_failed"
    assert body["confidence"] == "low"
    steps = [step["step"] for step in body["agent_trace"]]
    assert steps == (
        ["prepare_baseline", "query_rewrite", "prompt_build", "model_generation"]
        + ([] if failure == "timeout" else ["model_output_parse"])
        + ["rule_fallback"]
    )
    assert body["agent_trace"][-2]["status"] == "failed"
    assert calls == (2 if failure == "timeout" else 1)
    assert outbound.is_closed
