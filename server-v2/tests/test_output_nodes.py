import asyncio
import json
from pathlib import Path

import pytest

from app.agent.nodes import BuildResponseNode, ParseModelOutputNode, RuleFallbackNode
from app.agent.state import AgentPhase, VehicleAgentState
from app.providers.chat import ChatResult
from app.schemas.agent_trace import AgentTraceStep, TraceStatus
from app.schemas.qa import AnswerMode, ConfidenceLevel, VehicleQARequest
from app.services.generation.answer_parser import VehicleAnswerParser
from app.services.generation.qa_service import RuleFallbackQAService


def generated_state() -> VehicleAgentState:
    path = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"
    request = VehicleQARequest.model_validate(json.loads(path.read_text(encoding="utf-8")))
    return VehicleAgentState(
        request=request,
        phase=AgentPhase.MODEL_GENERATED,
        baseline_response=asyncio.run(RuleFallbackQAService().answer(request)),
        chat_result=ChatResult(
            content=json.dumps(
                {
                    "answer": "Check the fan.",
                    "findings": ["High temperature"],
                    "recommendations": ["Inspect cooling system"],
                }
            ),
            provider="stub",
            model="stub-chat",
            finish_reason="stop",
            input_tokens=100,
            output_tokens=20,
        ),
        trace=[AgentTraceStep(step="model_generation", status=TraceStatus.COMPLETED)],
    )


def test_parse_then_build_response_preserves_snapshots() -> None:
    initial = generated_state()
    parsed = ParseModelOutputNode(answer_parser=VehicleAnswerParser()).run(initial)
    final = BuildResponseNode().run(parsed)
    assert initial.phase is AgentPhase.MODEL_GENERATED
    assert initial.generated_answer is None
    assert len(initial.trace) == 1
    assert parsed.phase is AgentPhase.OUTPUT_PARSED
    assert parsed.final_response is None
    assert final.phase is AgentPhase.COMPLETED
    assert final.final_response is not None
    assert final.final_response.answer == "Check the fan."
    assert final.final_response.findings == ["High temperature"]
    assert final.final_response.recommendations == ["Inspect cooling system"]
    assert final.final_response.answer_mode is AnswerMode.LLM_ONLY
    assert final.baseline_response is not None
    assert final.final_response.severity == final.baseline_response.severity
    assert final.final_response.agent_trace == final.trace
    assert [step.step for step in final.trace] == [
        "model_generation",
        "model_output_parse",
        "build_response",
    ]
    with pytest.raises(ValueError):
        BuildResponseNode().run(final)


@pytest.mark.parametrize(
    ("content", "finish"),
    [
        ("not json", "stop"),
        ('{"findings": []}', "stop"),
        ('{"answer": "Valid JSON but incomplete generation"}', "length"),
    ],
)
def test_invalid_output_routes_to_rule_response(content: str, finish: str) -> None:
    initial = generated_state()
    assert initial.chat_result is not None
    initial = initial.model_copy(
        update={
            "chat_result": initial.chat_result.model_copy(
                update={
                    "content": content,
                    "finish_reason": finish,
                }
            ),
        }
    )
    failed = ParseModelOutputNode(answer_parser=VehicleAnswerParser()).run(initial)
    assert failed.phase is AgentPhase.FALLBACK
    assert failed.failure_code == "invalid_response"
    assert failed.final_response is None
    assert failed.trace[-1].status is TraceStatus.FAILED
    if finish == "length":
        assert "length" in failed.trace[-1].detail
    final = RuleFallbackNode().run(failed)
    assert final.phase is AgentPhase.COMPLETED
    assert final.final_response is not None and initial.baseline_response is not None
    assert final.final_response.answer == initial.baseline_response.answer
    assert final.final_response.recommendations == initial.baseline_response.recommendations
    assert final.final_response.answer_mode is AnswerMode.LLM_CALL_FAILED
    assert final.final_response.confidence is ConfidenceLevel.LOW
    assert final.final_response.agent_trace == final.trace
    assert failed.final_response is None
    with pytest.raises(ValueError):
        RuleFallbackNode().run(final)


def test_output_nodes_reject_missing_data() -> None:
    state = generated_state()
    with pytest.raises(ValueError, match="chat_result"):
        ParseModelOutputNode(answer_parser=VehicleAnswerParser()).run(
            state.model_copy(update={"chat_result": None})
        )
    with pytest.raises(ValueError, match="generated_answer"):
        BuildResponseNode().run(state.model_copy(update={"phase": AgentPhase.OUTPUT_PARSED}))
    with pytest.raises(ValueError, match="failure_code"):
        RuleFallbackNode().run(state.model_copy(update={"phase": AgentPhase.FALLBACK}))
