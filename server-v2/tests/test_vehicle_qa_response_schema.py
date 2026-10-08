import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.qa import AnswerMode, ConfidenceLevel, VehicleQAResponse
from app.schemas.rule_summary import DiagnosticSeverity


def _fixture_response_data() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "vehicle_qa_response.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_vehicle_qa_response_parses_complete_contract_fixture() -> None:
    response = VehicleQAResponse.model_validate(_fixture_response_data())

    assert response.severity is DiagnosticSeverity.WARNING
    assert response.answer_mode is AnswerMode.LLM_RAG
    assert response.confidence is ConfidenceLevel.MEDIUM
    assert response.sources[0].score == 0.82
    assert response.agent_trace[-1].step == "evidence_gate"


@pytest.mark.parametrize("severity", ["NORMAL", "NOTICE", "WARNING", "HIGH"])
def test_vehicle_qa_response_accepts_known_severity(severity: str) -> None:
    data = _fixture_response_data()
    data["severity"] = severity

    response = VehicleQAResponse.model_validate(data)

    assert response.severity is DiagnosticSeverity(severity)


@pytest.mark.parametrize(
    "answer_mode",
    [
        "llm_only",
        "llm_rag",
        "rule_fallback",
        "insufficient_retrieval_evidence",
        "llm_not_configured",
        "llm_call_failed",
    ],
)
def test_vehicle_qa_response_accepts_known_answer_modes(answer_mode: str) -> None:
    data = _fixture_response_data()
    data["answer_mode"] = answer_mode

    response = VehicleQAResponse.model_validate(data)

    assert response.answer_mode is AnswerMode(answer_mode)


@pytest.mark.parametrize("confidence", ["low", "medium", "high"])
def test_vehicle_qa_response_accepts_known_confidence_levels(confidence: str) -> None:
    data = _fixture_response_data()
    data["confidence"] = confidence

    response = VehicleQAResponse.model_validate(data)

    assert response.confidence is ConfidenceLevel(confidence)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("severity", "CRITICAL"),
        ("answer_mode", "sometimes_rag"),
        ("confidence", "mostly_sure"),
    ],
)
def test_vehicle_qa_response_rejects_unknown_control_value(field: str, invalid_value: str) -> None:
    data = _fixture_response_data()
    data[field] = invalid_value

    with pytest.raises(ValidationError):
        VehicleQAResponse.model_validate(data)


@pytest.mark.parametrize("field", ["answer", "rewritten_query"])
def test_vehicle_qa_response_rejects_blank_required_text(field: str) -> None:
    data = _fixture_response_data()
    data[field] = "   "

    with pytest.raises(ValidationError):
        VehicleQAResponse.model_validate(data)


def test_vehicle_qa_response_supplies_independent_list_defaults() -> None:
    first = VehicleQAResponse(
        answer="Check the cooling system.",
        severity="NOTICE",
        rewritten_query="cooling system checks",
        answer_mode="rule_fallback",
        confidence="low",
    )
    second = VehicleQAResponse(
        answer="Check the cooling system.",
        severity="NOTICE",
        rewritten_query="cooling system checks",
        answer_mode="rule_fallback",
        confidence="low",
    )

    first.findings.append("Coolant temperature increased.")

    assert second.findings == []
    assert second.sources == []
    assert second.agent_trace == []
