import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.agent_trace import AgentTraceStep, TraceStatus


@pytest.mark.parametrize(
    "status",
    ["completed", "passed", "fallback", "failed", "skipped"],
)
def test_agent_trace_accepts_known_status(status: str) -> None:
    trace = AgentTraceStep(step="plan", status=status, detail="test detail")

    assert trace.status is TraceStatus(status)


def test_agent_trace_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        AgentTraceStep(step="evidence_gate", status="[assed", detail="typo")


def test_response_fixture_contains_valid_trace_steps() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "vehicle_qa_response.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    traces = [AgentTraceStep.model_validate(item) for item in payload["agent_trace"]]

    assert len(traces) == 3


@pytest.mark.parametrize("step", ["", "   "])
def test_agent_trace_rejects_blank_step(step: str) -> None:
    with pytest.raises(ValidationError):
        AgentTraceStep(step=step, status="completed")


def test_agent_trace_strips_surrounding_whitespace() -> None:
    trace = AgentTraceStep(
        step="  retrieval_tool  ",
        status="completed",
        detail="  retrieval completed  ",
    )

    assert trace.step == "retrieval_tool"
    assert trace.detail == "retrieval completed"


def test_agent_trace_normalizes_whitespace_only_detail() -> None:
    trace = AgentTraceStep(step="plan", status="completed", detail="   ")

    assert trace.detail == ""
