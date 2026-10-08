import asyncio
import json
from pathlib import Path

import pytest

from app.agent.nodes import BuildPromptNode, PrepareBaselineNode
from app.agent.state import AgentPhase, VehicleAgentState
from app.schemas.agent_trace import TraceStatus
from app.schemas.qa import VehicleQARequest
from app.services.generation.prompt_builder import VehicleQAPromptBuilder
from app.services.generation.qa_service import RuleFallbackQAService


def initial_state() -> VehicleAgentState:
    path = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"
    request = VehicleQARequest.model_validate(json.loads(path.read_text(encoding="utf-8")))
    return VehicleAgentState(request=request)


def test_build_prompt_preserves_baseline_and_previous_snapshot() -> None:
    prepared = asyncio.run(
        PrepareBaselineNode(fallback=RuleFallbackQAService()).run(initial_state())
    )
    builder = VehicleQAPromptBuilder()

    updated = BuildPromptNode(prompt_builder=builder).run(prepared)

    assert updated is not prepared
    assert prepared.phase is AgentPhase.BASELINE_PREPARED
    assert prepared.chat_request is None
    assert len(prepared.trace) == 1
    assert updated.phase is AgentPhase.PROMPT_BUILT
    assert updated.chat_request == builder.build(prepared.request)
    assert updated.baseline_response == prepared.baseline_response
    assert updated.trace[:-1] == prepared.trace
    assert updated.trace[-1].step == "prompt_build"
    assert updated.trace[-1].status is TraceStatus.COMPLETED
    assert updated.final_response is None


@pytest.mark.parametrize("phase", [AgentPhase.RECEIVED, AgentPhase.PROMPT_BUILT])
def test_build_prompt_rejects_wrong_phase(phase: AgentPhase) -> None:
    state = initial_state().model_copy(update={"phase": phase})

    with pytest.raises(ValueError, match="phase=baseline_prepared"):
        BuildPromptNode(prompt_builder=VehicleQAPromptBuilder()).run(state)


def test_build_prompt_rejects_missing_baseline() -> None:
    state = initial_state().model_copy(update={"phase": AgentPhase.BASELINE_PREPARED})

    with pytest.raises(ValueError, match="baseline_response"):
        BuildPromptNode(prompt_builder=VehicleQAPromptBuilder()).run(state)
