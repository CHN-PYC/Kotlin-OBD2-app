import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.routes.qa import get_vehicle_qa_service
from app.core.config import Settings
from app.main import create_app
from app.schemas.qa import VehicleQARequest, VehicleQAResponse
from app.services.generation.deadline import DeadlineQAService
from app.services.generation.qa_service import RuleFallbackQAService

FIXTURE = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"


def test_fast_service_response_is_preserved() -> None:
    async def run() -> None:
        request = VehicleQARequest.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
        baseline = RuleFallbackQAService()
        result = await DeadlineQAService(baseline, seconds=1).answer(request)
        assert result == await baseline.answer(request)

    asyncio.run(run())


def test_api_deadline_cancels_slow_service_and_returns_rule_answer() -> None:
    class SlowService:
        cancelled = False

        async def answer(self, request: VehicleQARequest) -> VehicleQAResponse:
            try:
                await asyncio.Event().wait()
            finally:
                self.cancelled = True
            raise AssertionError("unreachable")

    service = SlowService()
    app = create_app(settings=Settings(_env_file=None, request_deadline_seconds=0.02))
    app.dependency_overrides[get_vehicle_qa_service] = lambda: service
    with TestClient(app) as client:
        response = client.post("/qa/vehicle", json=json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert response.status_code == 200
    data = response.json()
    assert data["answer_mode"] == "rule_fallback"
    assert data["confidence"] == "low"
    assert [step["step"] for step in data["agent_trace"]] == ["request_deadline", "rule_fallback"]
    assert service.cancelled


def test_dependency_timeout_is_not_mislabelled_as_deadline() -> None:
    class BrokenService:
        async def answer(self, request: VehicleQARequest) -> VehicleQAResponse:
            raise TimeoutError("dependency timeout")

    async def run() -> None:
        request = VehicleQARequest.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
        with pytest.raises(TimeoutError, match="dependency timeout"):
            await DeadlineQAService(BrokenService(), seconds=1).answer(request)

    asyncio.run(run())


def test_external_cancellation_propagates() -> None:
    class CancelledService:
        async def answer(self, request: VehicleQARequest) -> VehicleQAResponse:
            raise asyncio.CancelledError()

    async def run() -> None:
        request = VehicleQARequest.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
        with pytest.raises(asyncio.CancelledError):
            await DeadlineQAService(CancelledService(), seconds=1).answer(request)

    asyncio.run(run())
