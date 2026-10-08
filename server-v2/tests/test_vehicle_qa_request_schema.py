import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.qa import VehicleQARequest


def _fixture_request_data() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_vehicle_qa_request_parses_complete_contract_fixture() -> None:
    request = VehicleQARequest.model_validate(_fixture_request_data())

    assert request.session_id == "10001"
    assert request.vehicle_context.session_summary.sample_count == 180
    assert request.rule_summary is not None
    assert request.rule_summary.findings[0].code == "COOLANT_HIGH"
    assert request.top_k == 5


def test_vehicle_qa_request_defaults_top_k_to_five() -> None:
    data = _fixture_request_data()
    data.pop("top_k")

    request = VehicleQARequest.model_validate(data)

    assert request.top_k == 5


@pytest.mark.parametrize("top_k", [0, 21])
def test_vehicle_qa_request_rejects_top_k_outside_limit(top_k: int) -> None:
    data = _fixture_request_data()
    data["top_k"] = top_k

    with pytest.raises(ValidationError):
        VehicleQARequest.model_validate(data)


def test_vehicle_qa_request_rejects_string_top_k() -> None:
    data = _fixture_request_data()
    data["top_k"] = "5"

    with pytest.raises(ValidationError):
        VehicleQARequest.model_validate(data)


@pytest.mark.parametrize("field", ["session_id", "question"])
def test_vehicle_qa_request_rejects_blank_identity_text(field: str) -> None:
    data = _fixture_request_data()
    data[field] = "   "

    with pytest.raises(ValidationError):
        VehicleQARequest.model_validate(data)


def test_vehicle_qa_request_rejects_oversized_question() -> None:
    data = _fixture_request_data()
    data["question"] = "x" * 1001

    with pytest.raises(ValidationError):
        VehicleQARequest.model_validate(data)


def test_vehicle_qa_request_rejects_integer_session_id() -> None:
    data = _fixture_request_data()
    data["session_id"] = 10001

    with pytest.raises(ValidationError):
        VehicleQARequest.model_validate(data)


def test_vehicle_qa_request_allows_missing_rule_summary() -> None:
    data = _fixture_request_data()
    data.pop("rule_summary")

    request = VehicleQARequest.model_validate(data)

    assert request.rule_summary is None


def test_vehicle_qa_request_rejects_unknown_top_level_field() -> None:
    data = _fixture_request_data()
    data["topK"] = data.pop("top_k")

    with pytest.raises(ValidationError):
        VehicleQARequest.model_validate(data)
