import asyncio
import json
from pathlib import Path

import pytest

from app.agent.nodes import BuildPromptNode, GenerateModelNode, PrepareBaselineNode
from app.agent.state import AgentPhase, VehicleAgentState
from app.providers.chat import ChatRequest, ChatResult
from app.providers.errors import ModelTimeoutError
from app.schemas.agent_trace import TraceStatus
from app.schemas.qa import VehicleQARequest
from app.services.generation.prompt_builder import VehicleQAPromptBuilder
from app.services.generation.qa_service import RuleFallbackQAService


class StubChatModel:
    provider_name = "stub"
    model_name = "stub-chat"

    def __init__(self, outcome: ChatResult | Exception) -> None:
        self.outcome = outcome
        self.requests: list[ChatRequest] = []

    async def generate(self, request: ChatRequest) -> ChatResult:
        self.requests.append(request)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def ready_state() -> VehicleAgentState:
    path = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"
    request = VehicleQARequest.model_validate(json.loads(path.read_text(encoding="utf-8")))
    baseline = asyncio.run(
        PrepareBaselineNode(fallback=RuleFallbackQAService()).run(
            VehicleAgentState(request=request)
        )
    )
    return BuildPromptNode(prompt_builder=VehicleQAPromptBuilder()).run(baseline)


def model_result() -> ChatResult:
    return ChatResult(
        content='{"answer":"Inspect the cooling system."}',
        provider="stub",
        model="stub-chat",
        finish_reason="stop",
        input_tokens=100,
        output_tokens=12,
    )


def test_generate_model_preserves_history_and_stores_result() -> None:
    initial = ready_state()
    result = model_result()
    model = StubChatModel(result)

    updated = asyncio.run(GenerateModelNode(model=model).run(initial))

    assert model.requests == [initial.chat_request]
    assert updated is not initial
    assert initial.phase is AgentPhase.PROMPT_BUILT
    assert initial.chat_result is None
    assert len(initial.trace) == 2
    assert updated.phase is AgentPhase.MODEL_GENERATED
    assert updated.chat_result == result
    assert updated.baseline_response == initial.baseline_response
    assert updated.failure_code is None
    assert updated.final_response is None
    assert updated.trace[:-1] == initial.trace
    assert updated.trace[-1].step == "model_generation"
    assert updated.trace[-1].status is TraceStatus.COMPLETED


def test_generate_model_marks_provider_failure_for_fallback() -> None:
    initial = ready_state()
    model = StubChatModel(ModelTimeoutError("slow", provider="stub", model="stub-chat"))

    updated = asyncio.run(GenerateModelNode(model=model).run(initial))

    assert len(model.requests) == 1
    assert initial.failure_code is None
    assert len(initial.trace) == 2
    assert updated.phase is AgentPhase.FALLBACK
    assert updated.failure_code == "timeout"
    assert updated.chat_result is None
    assert updated.final_response is None
    assert updated.baseline_response == initial.baseline_response
    assert updated.trace[:-1] == initial.trace
    assert updated.trace[-1].step == "model_generation"
    assert updated.trace[-1].status is TraceStatus.FAILED
    assert "timeout" in updated.trace[-1].detail


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("phase", AgentPhase.MODEL_GENERATED, "phase=prompt_built"),
        ("chat_request", None, "chat_request"),
        ("baseline_response", None, "baseline_response"),
    ],
)
def test_generate_model_rejects_invalid_state_before_calling_provider(
    field: str, value: object, message: str
) -> None:
    state = ready_state().model_copy(update={field: value})
    model = StubChatModel(model_result())

    with pytest.raises(ValueError, match=message):
        asyncio.run(GenerateModelNode(model=model).run(state))

    assert model.requests == []


def test_generate_model_does_not_hide_programming_errors() -> None:
    state = ready_state()
    model = StubChatModel(TypeError("implementation bug"))

    with pytest.raises(TypeError, match="implementation bug"):
        asyncio.run(GenerateModelNode(model=model).run(state))
