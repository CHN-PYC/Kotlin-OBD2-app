import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from app.agent.state import AgentPhase, VehicleAgentState
from app.agent.workflow import WorkFlow
from app.schemas.memory import SessionMemory
from app.schemas.qa import VehicleQARequest
from app.services.generation.qa_service import RuleFallbackQAService
from app.services.generation.workflow_qa_service import WorkflowQAService


def request_fixture() -> VehicleQARequest:
    path = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"
    return VehicleQARequest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def test_adapter_returns_only_final_response() -> None:
    request = request_fixture()
    response = asyncio.run(RuleFallbackQAService().answer(request))
    state = VehicleAgentState(request=request, phase=AgentPhase.COMPLETED, final_response=response)
    workflow = Mock(spec=WorkFlow)
    workflow.run = AsyncMock(return_value=state)
    actual = asyncio.run(WorkflowQAService(workflow=workflow).answer(request))
    assert actual is state.final_response
    workflow.run.assert_awaited_once_with(
        request,
        session_memory=SessionMemory(session_id=request.session_id),
    )


@pytest.mark.parametrize("phase", [AgentPhase.RECEIVED, AgentPhase.COMPLETED])
def test_adapter_rejects_missing_final_response(phase: AgentPhase) -> None:
    request = request_fixture()
    workflow = Mock(spec=WorkFlow)
    workflow.run = AsyncMock(return_value=VehicleAgentState(request=request, phase=phase))
    with pytest.raises(RuntimeError, match="final_response"):
        asyncio.run(WorkflowQAService(workflow=workflow).answer(request))
