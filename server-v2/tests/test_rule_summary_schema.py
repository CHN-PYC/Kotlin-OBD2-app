import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.rule_summary import DiagnosticSeverity, RuleFinding, RuleSummary


def _valid_finding_data() -> dict:
    return {
        "code": "COOLANT_HIGH",
        "severity": "WARNING",
        "title": "Coolant temperature is high",
        "detail": "Maximum coolant temperature reached 108 C.",
    }


def test_request_fixture_contains_valid_rule_summary() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    summary = RuleSummary.model_validate(payload["rule_summary"])

    assert summary.severity is DiagnosticSeverity.WARNING
    assert summary.findings[0].code == "COOLANT_HIGH"


@pytest.mark.parametrize("severity", ["NORMAL", "NOTICE", "WARNING", "HIGH"])
def test_rule_finding_accepts_known_severity(severity: str) -> None:
    data = _valid_finding_data()
    data["severity"] = severity

    finding = RuleFinding.model_validate(data)

    assert finding.severity is DiagnosticSeverity(severity)


def test_rule_finding_rejects_unknown_severity() -> None:
    data = _valid_finding_data()
    data["severity"] = "WARNNING"

    with pytest.raises(ValidationError):
        RuleFinding.model_validate(data)


@pytest.mark.parametrize("field", ["code", "title", "detail"])
def test_rule_finding_rejects_blank_required_text(field: str) -> None:
    data = _valid_finding_data()
    data[field] = "   "

    with pytest.raises(ValidationError):
        RuleFinding.model_validate(data)


def test_rule_summary_supplies_independent_list_defaults() -> None:
    first = RuleSummary(severity="NOTICE", summary="No urgent issue detected.")
    second = RuleSummary(severity="NOTICE", summary="No urgent issue detected.")

    first.recommendations.append("Continue monitoring.")

    assert second.findings == []
    assert second.recommendations == []


def test_rule_summary_rejects_recommendations_string() -> None:
    with pytest.raises(ValidationError):
        RuleSummary(
            severity="NOTICE",
            summary="No urgent issue detected.",
            recommendations="Continue monitoring.",
        )
