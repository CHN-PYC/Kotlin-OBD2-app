import asyncio
import json
from pathlib import Path

from app.providers.chat import ChatRequest, ChatResult
from app.providers.errors import ModelTimeoutError
from app.schemas.agent_trace import TraceStatus
from app.schemas.qa import AnswerMode, ConfidenceLevel, VehicleQARequest
from app.schemas.rule_summary import DiagnosticSeverity
from app.services.generation.answer_parser import VehicleAnswerParser
from app.services.generation.prompt_builder import VehicleQAPromptBuilder
from app.services.generation.qa_service import LLMVehicleQAService, RuleFallbackQAService

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"


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


def load_request() -> VehicleQARequest:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return VehicleQARequest.model_validate(payload)


def result(*, finish_reason: str = "stop") -> ChatResult:
    return ChatResult(
        content=json.dumps(
            {
                "answer": "Check the coolant level, fan, thermostat, and radiator first.",
                "findings": ["Coolant temperature reached 108 C."],
                "recommendations": ["Stop safely if the temperature continues to rise."],
            }
        ),
        provider="stub",
        model="stub-chat",
        finish_reason=finish_reason,
        input_tokens=120,
        output_tokens=18,
    )


def create_service(model: StubChatModel) -> LLMVehicleQAService:
    return LLMVehicleQAService(
        model=model,
        prompt_builder=VehicleQAPromptBuilder(),
        answer_parser=VehicleAnswerParser(),
        fallback=RuleFallbackQAService(),
    )


def test_llm_service_returns_model_answer_with_rule_evidence() -> None:
    model = StubChatModel(result())

    response = asyncio.run(create_service(model).answer(load_request()))

    assert response.answer == "Check the coolant level, fan, thermostat, and radiator first."
    assert response.findings == ["Coolant temperature reached 108 C."]
    assert response.recommendations == ["Stop safely if the temperature continues to rise."]
    assert response.answer_mode is AnswerMode.LLM_ONLY
    assert response.confidence is ConfidenceLevel.MEDIUM
    assert response.severity is DiagnosticSeverity.WARNING
    assert response.sources == []
    assert [step.step for step in response.agent_trace] == [
        "prompt_build",
        "model_generation",
        "model_output_parse",
    ]
    assert all(step.status is TraceStatus.COMPLETED for step in response.agent_trace)
    assert len(model.requests) == 1


def test_llm_service_falls_back_when_provider_fails() -> None:
    error = ModelTimeoutError("too slow", provider="stub", model="stub-chat")
    model = StubChatModel(error)
    request = load_request()

    response = asyncio.run(create_service(model).answer(request))

    assert response.answer == request.rule_summary.summary
    assert response.answer_mode is AnswerMode.LLM_CALL_FAILED
    assert response.confidence is ConfidenceLevel.LOW
    assert [step.status for step in response.agent_trace] == [
        TraceStatus.FAILED,
        TraceStatus.FALLBACK,
    ]
    assert "timeout" in response.agent_trace[0].detail


def test_llm_service_rejects_truncated_model_answer() -> None:
    model = StubChatModel(result(finish_reason="length"))

    response = asyncio.run(create_service(model).answer(load_request()))

    assert response.answer_mode is AnswerMode.LLM_CALL_FAILED
    assert response.confidence is ConfidenceLevel.LOW
    assert response.agent_trace[0].status is TraceStatus.FAILED
    assert "length" in response.agent_trace[0].detail


def test_llm_service_falls_back_when_model_output_has_invalid_schema() -> None:
    invalid_result = result().model_copy(update={"content": '{"findings": []}'})
    model = StubChatModel(invalid_result)

    response = asyncio.run(create_service(model).answer(load_request()))

    assert response.answer_mode is AnswerMode.LLM_CALL_FAILED
    assert response.confidence is ConfidenceLevel.LOW
    assert [step.status for step in response.agent_trace] == [
        TraceStatus.FAILED,
        TraceStatus.FALLBACK,
    ]
    assert "invalid_response" in response.agent_trace[0].detail
