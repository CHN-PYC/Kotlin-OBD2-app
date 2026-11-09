import asyncio
import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.routes.qa import get_vehicle_qa_service
from app.core.config import Settings
from app.main import create_app
from app.schemas.qa import VehicleQARequest, VehicleQAResponse
from app.services.generation.exception_fallback import ExceptionFallbackQAService
from app.services.generation.qa_service import RuleFallbackQAService

FIXTURE = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"


def _request() -> VehicleQARequest:
    return VehicleQARequest.model_validate_json(FIXTURE.read_text(encoding="utf-8"))


class BrokenService:
    async def answer(self, request: VehicleQARequest) -> VehicleQAResponse:
        raise RuntimeError("secret detail http://internal:8080")


def test_successful_response_is_unchanged() -> None:
    async def run() -> None:
        baseline = RuleFallbackQAService()
        result = await ExceptionFallbackQAService(baseline).answer(_request())
        assert result == await baseline.answer(_request())

    asyncio.run(run())


def test_unexpected_error_returns_rule_fallback_without_leaking_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def run() -> VehicleQAResponse:
        return await ExceptionFallbackQAService(BrokenService()).answer(_request())

    with caplog.at_level(logging.WARNING):
        result = asyncio.run(run())

    assert result.answer_mode == "rule_fallback"
    assert [step.step for step in result.agent_trace] == ["unexpected_error", "rule_fallback"]
    assert "secret detail" not in result.model_dump_json()
    assert "type=RuntimeError" in caplog.text
    assert "secret detail" not in caplog.text


def test_cancellation_propagates() -> None:
    class CancelledService:
        async def answer(self, request: VehicleQARequest) -> VehicleQAResponse:
            raise asyncio.CancelledError()

    async def run() -> None:
        with pytest.raises(asyncio.CancelledError):
            await ExceptionFallbackQAService(CancelledService()).answer(_request())

    asyncio.run(run())


def test_failing_fallback_is_not_swallowed() -> None:
    async def run() -> None:
        service = ExceptionFallbackQAService(BrokenService(), fallback=BrokenService())
        with pytest.raises(RuntimeError):
            await service.answer(_request())

    asyncio.run(run())


def test_api_returns_rule_fallback_instead_of_500() -> None:
    app = create_app(settings=Settings(_env_file=None))
    app.dependency_overrides[get_vehicle_qa_service] = BrokenService
    with TestClient(app) as client:
        response = client.post("/qa/vehicle", json=json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert response.status_code == 200
    data = response.json()
    assert data["answer_mode"] == "rule_fallback"
    assert [step["step"] for step in data["agent_trace"]] == ["unexpected_error", "rule_fallback"]
