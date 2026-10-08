import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agent.state import AgentPhase, VehicleAgentState
from app.providers.chat import ChatRequest
from app.schemas.agent_trace import AgentTraceStep, TraceStatus
from app.schemas.qa import VehicleQARequest
from app.services.generation.prompt_builder import VehicleQAPromptBuilder
from app.services.generation.qa_service import RuleFallbackQAService

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"


def load_request() -> VehicleQARequest:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return VehicleQARequest.model_validate(payload)


def test_agent_state_starts_with_only_validated_input() -> None:
    state = VehicleAgentState(request=load_request())

    assert state.phase is AgentPhase.RECEIVED
    assert state.baseline_response is None
    assert state.chat_request is None
    assert state.chat_result is None
    assert state.generated_answer is None
    assert state.final_response is None
    assert state.failure_code is None
    assert state.trace == []
    assert AgentPhase.RECEIVED.value == "received"


def test_agent_state_accepts_rule_response_as_baseline() -> None:
    request = load_request()
    baseline = asyncio.run(RuleFallbackQAService().answer(request))

    state = VehicleAgentState(request=request, baseline_response=baseline)

    assert state.baseline_response == baseline


def test_agent_state_can_create_a_new_prompt_built_snapshot() -> None:
    initial = VehicleAgentState(request=load_request())
    prompt = VehicleQAPromptBuilder().build(initial.request)
    step = AgentTraceStep(
        step="prompt_build",
        status=TraceStatus.COMPLETED,
        detail="Built structured vehicle evidence prompt.",
    )

    updated = initial.model_copy(
        update={
            "phase": AgentPhase.PROMPT_BUILT,
            "chat_request": prompt,
            "trace": [*initial.trace, step],
        }
    )

    assert initial.phase is AgentPhase.RECEIVED
    assert initial.chat_request is None
    assert updated.phase is AgentPhase.PROMPT_BUILT
    assert isinstance(updated.chat_request, ChatRequest)
    assert updated.trace == [step]


def test_agent_state_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        VehicleAgentState.model_validate(
            {
                "request": load_request(),
                "unexpected": "not part of workflow state",
            }
        )
