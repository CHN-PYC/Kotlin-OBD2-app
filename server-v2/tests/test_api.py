import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _request_fixture() -> dict:
    path = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(
        settings=Settings(
            _env_file=None,
            model_provider="ollama",
            ollama_chat_model=None,
        )
    )
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint_reports_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_vehicle_qa_endpoint_accepts_android_contract(client: TestClient) -> None:
    response = client.post("/qa/vehicle", json=_request_fixture())

    assert response.status_code == 200
    payload = response.json()
    assert payload["severity"] == "WARNING"
    assert payload["answer_mode"] == "rule_fallback"
    assert payload["confidence"] == "low"
    assert payload["sources"] == []
    assert payload["agent_trace"][0]["status"] == "fallback"


def test_vehicle_qa_endpoint_accepts_optional_authorization_header(client: TestClient) -> None:
    response = client.post(
        "/qa/vehicle",
        json=_request_fixture(),
        headers={"Authorization": "Bearer local-development-key"},
    )

    assert response.status_code == 200


@pytest.mark.parametrize("authorization", [None, "Bearer wrong-key", "Basic service-key"])
def test_vehicle_qa_endpoint_rejects_missing_or_invalid_configured_api_key(
    authorization: str | None,
) -> None:
    app = create_app(
        settings=Settings(
            _env_file=None,
            api_key="service-key",
            model_provider="ollama",
            ollama_chat_model=None,
        )
    )
    headers = {} if authorization is None else {"Authorization": authorization}
    with TestClient(app) as secured_client:
        response = secured_client.post("/qa/vehicle", json=_request_fixture(), headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_vehicle_qa_endpoint_accepts_correct_configured_api_key() -> None:
    app = create_app(
        settings=Settings(
            _env_file=None,
            api_key="service-key",
            model_provider="ollama",
            ollama_chat_model=None,
        )
    )
    with TestClient(app) as secured_client:
        response = secured_client.post(
            "/qa/vehicle",
            json=_request_fixture(),
            headers={"Authorization": "Bearer service-key"},
        )

    assert response.status_code == 200


def test_vehicle_qa_endpoint_rejects_invalid_top_k(client: TestClient) -> None:
    payload = _request_fixture()
    payload["top_k"] = 0

    response = client.post("/qa/vehicle", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "top_k"]


def test_vehicle_qa_endpoint_rejects_unknown_top_level_field(client: TestClient) -> None:
    payload = _request_fixture()
    payload["unexpected"] = True

    response = client.post("/qa/vehicle", json=payload)

    assert response.status_code == 422


def test_openapi_exposes_vehicle_qa_contract(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/qa/vehicle" in response.json()["paths"]
