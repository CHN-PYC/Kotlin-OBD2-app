import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.vehicle_context import PromptHints, VehicleContext, VehicleSourceType


def _fixture_context_data() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return payload["vehicle_context"]


def test_vehicle_context_parses_complete_android_payload() -> None:
    context = VehicleContext.model_validate(_fixture_context_data())

    assert context.source_type is VehicleSourceType.REAL
    assert context.session_summary.sample_count == 180
    assert context.sample_highlights.hottest_sample is not None
    assert context.prompt_hints.is_demo_data is False


@pytest.mark.parametrize("source_type", ["REAL", "DEMO", "REPLAY"])
def test_vehicle_context_accepts_known_source_types(source_type: str) -> None:
    data = _fixture_context_data()
    data["sourceType"] = source_type
    data["promptHints"]["isDemoData"] = source_type == "DEMO"

    context = VehicleContext.model_validate(data)

    assert context.source_type is VehicleSourceType(source_type)


def test_vehicle_context_rejects_unknown_source_type() -> None:
    data = _fixture_context_data()
    data["sourceType"] = "SYNTHETIC"

    with pytest.raises(ValidationError):
        VehicleContext.model_validate(data)


@pytest.mark.parametrize(
    ("source_type", "is_demo_data"),
    [("DEMO", False), ("REAL", True), ("REPLAY", True)],
)
def test_vehicle_context_rejects_inconsistent_demo_flag(
    source_type: str, is_demo_data: bool
) -> None:
    data = _fixture_context_data()
    data["sourceType"] = source_type
    data["promptHints"]["isDemoData"] = is_demo_data

    with pytest.raises(ValidationError):
        VehicleContext.model_validate(data)


def test_prompt_hints_rejects_string_boolean() -> None:
    with pytest.raises(ValidationError):
        PromptHints(
            isDemoData="false",
            shouldAvoidHardFaultClaims=False,
            instruction="Use real vehicle evidence carefully.",
        )


def test_prompt_hints_rejects_blank_instruction() -> None:
    with pytest.raises(ValidationError):
        PromptHints(
            isDemoData=False,
            shouldAvoidHardFaultClaims=False,
            instruction="   ",
        )


def test_vehicle_context_rejects_negative_created_at() -> None:
    data = _fixture_context_data()
    data["createdAt"] = -1

    with pytest.raises(ValidationError):
        VehicleContext.model_validate(data)
