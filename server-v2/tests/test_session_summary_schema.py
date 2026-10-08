import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.vehicle_context import SessionSummary


def _fixture_summary_data() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return payload["vehicle_context"]["sessionSummary"]


def test_session_summary_reads_android_camel_case_fields() -> None:
    summary = SessionSummary.model_validate(_fixture_summary_data())

    assert summary.duration_sec == 900
    assert summary.avg_coolant_temp == 96.5
    assert summary.max_battery_voltage == 14.2


def test_session_summary_serializes_back_to_android_field_names() -> None:
    summary = SessionSummary.model_validate(_fixture_summary_data())

    serialized = summary.model_dump(by_alias=True)

    assert serialized["sampleCount"] == 180
    assert serialized["avgEngineLoad"] == 38.0
    assert "sample_count" not in serialized


def test_session_summary_also_accepts_python_field_names() -> None:
    data = _fixture_summary_data()
    data["duration_sec"] = data.pop("durationSec")

    summary = SessionSummary.model_validate(data)

    assert summary.duration_sec == 900


@pytest.mark.parametrize("field", ["durationSec", "sampleCount", "maxSpeed", "maxRpm"])
def test_session_summary_rejects_negative_counts_and_maximums(field: str) -> None:
    data = _fixture_summary_data()
    data[field] = -1

    with pytest.raises(ValidationError):
        SessionSummary.model_validate(data)


def test_session_summary_rejects_string_number() -> None:
    data = _fixture_summary_data()
    data["sampleCount"] = "180"

    with pytest.raises(ValidationError):
        SessionSummary.model_validate(data)


@pytest.mark.parametrize("invalid_value", [float("nan"), float("inf"), float("-inf")])
def test_session_summary_rejects_non_finite_measurement(invalid_value: float) -> None:
    data = _fixture_summary_data()
    data["avgCoolantTemp"] = invalid_value

    with pytest.raises(ValidationError):
        SessionSummary.model_validate(data)
