import asyncio
import json
from pathlib import Path

import pytest

from app.agent.nodes import PrepareBaselineNode
from app.agent.state import AgentPhase, VehicleAgentState
from app.schemas.agent_trace import TraceStatus
from app.schemas.qa import AnswerMode, VehicleQARequest
from app.services.generation.qa_service import RuleFallbackQAService

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"


def load_state() -> VehicleAgentState:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    request = VehicleQARequest.model_validate(payload)
    return VehicleAgentState(request=request)


def test_prepare_baseline_node_returns_new_state_with_rule_response() -> None:
    initial = load_state()
    node = PrepareBaselineNode(fallback=RuleFallbackQAService())

    updated = asyncio.run(node.run(initial))

    assert initial.phase is AgentPhase.RECEIVED
    assert initial.baseline_response is None
    assert updated.phase is AgentPhase.BASELINE_PREPARED
    assert updated.baseline_response is not None
    assert updated.baseline_response.answer_mode is AnswerMode.RULE_FALLBACK
    assert updated.baseline_response.severity.value == "WARNING"
    assert updated.trace[-1].step == "prepare_baseline"
    assert updated.trace[-1].status is TraceStatus.COMPLETED


def test_prepare_baseline_node_rejects_wrong_input_phase() -> None:
    state = load_state().model_copy(update={"phase": AgentPhase.BASELINE_PREPARED})
    node = PrepareBaselineNode(fallback=RuleFallbackQAService())

    with pytest.raises(ValueError, match="phase=received"):
        asyncio.run(node.run(state))
