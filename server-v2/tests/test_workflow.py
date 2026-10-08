import asyncio
import json
from pathlib import Path

import pytest

from app.agent.nodes import (
    BuildPromptNode,
    BuildResponseNode,
    GenerateModelNode,
    ParseModelOutputNode,
    PrepareBaselineNode,
    RuleFallbackNode,
)
from app.agent.state import AgentPhase
from app.agent.workflow import WorkFlow
from app.providers.chat import ChatRequest, ChatResult
from app.providers.errors import ModelTimeoutError
from app.schemas.qa import AnswerMode, VehicleQARequest
from app.services.generation.answer_parser import VehicleAnswerParser
from app.services.generation.prompt_builder import VehicleQAPromptBuilder
from app.services.generation.qa_service import RuleFallbackQAService


class ScriptedModel:
    provider_name = "stub"
    model_name = "stub-chat"

    def __init__(self, outcomes: list[ChatResult | Exception]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    async def generate(self, request: ChatRequest) -> ChatResult:
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def request_fixture() -> VehicleQARequest:
    path = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"
    return VehicleQARequest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def result(
    content: str = '{"answer":"Inspect the cooling system."}', finish_reason: str = "stop"
) -> ChatResult:
    return ChatResult(
        content=content,
        finish_reason=finish_reason,
        provider="stub",
        model="stub-chat",
        input_tokens=100,
        output_tokens=20,
    )


def workflow(model: ScriptedModel) -> WorkFlow:
    return WorkFlow(
        prepare_node=PrepareBaselineNode(fallback=RuleFallbackQAService()),
        prompt_node=BuildPromptNode(prompt_builder=VehicleQAPromptBuilder()),
        generate_node=GenerateModelNode(model=model),
        parse_node=ParseModelOutputNode(answer_parser=VehicleAnswerParser()),
        fallback_node=RuleFallbackNode(),
        response_node=BuildResponseNode(),
    )


def test_workflow_completes_successful_path() -> None:
    model = ScriptedModel([result()])
    state = asyncio.run(workflow(model).run(request_fixture()))
    assert state.phase is AgentPhase.COMPLETED
    assert state.final_response is not None
    assert state.final_response.answer == "Inspect the cooling system."
    assert state.final_response.answer_mode is AnswerMode.LLM_ONLY
    assert state.final_response.agent_trace == state.trace
    assert [step.step for step in state.trace] == [
        "prepare_baseline",
        "prompt_build",
        "model_generation",
        "model_output_parse",
        "build_response",
    ]
    assert model.calls == 1


@pytest.mark.parametrize(
    ("outcome", "code", "parsed"),
    [
        (ModelTimeoutError("slow", provider="stub"), "timeout", False),
        (result("not-json"), "invalid_response", True),
        (result(finish_reason="length"), "invalid_response", True),
    ],
)
def test_workflow_failure_ends_in_rule_response(
    outcome: ChatResult | Exception,
    code: str,
    parsed: bool,
) -> None:
    model = ScriptedModel([outcome])
    state = asyncio.run(workflow(model).run(request_fixture()))
    assert state.phase is AgentPhase.COMPLETED
    assert state.failure_code == code
    assert state.final_response is not None and state.baseline_response is not None
    assert state.final_response.answer == state.baseline_response.answer
    assert state.final_response.answer_mode is AnswerMode.LLM_CALL_FAILED
    assert state.final_response.agent_trace == state.trace
    steps = [step.step for step in state.trace]
    assert steps[-1] == "rule_fallback"
    assert "build_response" not in steps
    assert ("model_output_parse" in steps) is parsed
    assert model.calls == 1


def test_workflow_starts_fresh_after_previous_failure() -> None:
    model = ScriptedModel([ModelTimeoutError("slow", provider="stub"), result()])
    runner = workflow(model)

    async def run_twice() -> None:
        first = await runner.run(request_fixture())
        original_trace = list(first.trace)
        second = await runner.run(request_fixture())
        assert first.failure_code == "timeout"
        assert second.failure_code is None
        assert first.trace == original_trace
        assert first.trace is not second.trace
        assert all(step.step != "rule_fallback" for step in second.trace)
        assert second.final_response is not None
        assert second.final_response.answer_mode is AnswerMode.LLM_ONLY

    asyncio.run(run_twice())
