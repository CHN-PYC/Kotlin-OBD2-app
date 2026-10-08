import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.vehicle_context import SampleHighlights, SamplePoint


def _fixture_highlights_data() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return payload["vehicle_context"]["sampleHighlights"]


def _valid_sample_data() -> dict:
    return _fixture_highlights_data()["hottestSample"]


def test_sample_highlights_parses_nested_sample_point() -> None:
    highlights = SampleHighlights.model_validate(_fixture_highlights_data())

    assert isinstance(highlights.hottest_sample, SamplePoint)
    assert highlights.hottest_sample.coolant_temp == 108
    assert highlights.lowest_voltage_sample is None


def test_sample_highlights_accepts_explicit_null() -> None:
    highlights = SampleHighlights.model_validate({"hottestSample": None})

    assert highlights.hottest_sample is None


def test_sample_highlights_allows_all_fields_to_be_omitted() -> None:
    highlights = SampleHighlights.model_validate({})

    assert highlights.hottest_sample is None
    assert highlights.representative_cruise_sample is None


@pytest.mark.parametrize("field", ["timestamp", "rpm", "speed"])
def test_sample_point_rejects_negative_identity_measurements(field: str) -> None:
    data = _valid_sample_data()
    data[field] = -1

    with pytest.raises(ValidationError):
        SamplePoint.model_validate(data)


def test_sample_point_rejects_string_rpm() -> None:
    data = _valid_sample_data()
    data["rpm"] = "2100"

    with pytest.raises(ValidationError):
        SamplePoint.model_validate(data)


@pytest.mark.parametrize("throttle_pos", [-1, 101])
def test_sample_point_rejects_invalid_throttle_percentage(throttle_pos: int) -> None:
    data = _valid_sample_data()
    data["throttlePos"] = throttle_pos

    with pytest.raises(ValidationError):
        SamplePoint.model_validate(data)


def test_sample_highlights_rejects_invalid_nested_sample() -> None:
    data = _fixture_highlights_data()
    data["hottestSample"]["engineLoad"] = float("nan")

    with pytest.raises(ValidationError):
        SampleHighlights.model_validate(data)
