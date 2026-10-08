import json

import pytest

from app.providers.chat import ChatResult
from app.providers.errors import InvalidModelResponseError
from app.schemas.generation import GeneratedVehicleAnswer
from app.services.generation.answer_parser import VehicleAnswerParser


def chat_result(content: str) -> ChatResult:
    return ChatResult(
        content=content,
        provider="stub",
        model="stub-chat",
        finish_reason="stop",
        input_tokens=100,
        output_tokens=20,
    )


def test_parser_returns_typed_vehicle_answer_from_json() -> None:
    content = json.dumps(
        {
            "answer": "Check the coolant level and cooling fan first.",
            "findings": ["Coolant temperature reached 108 C."],
            "recommendations": ["Stop safely if the temperature continues to rise."],
        }
    )

    parsed = VehicleAnswerParser().parse(chat_result(content))

    assert isinstance(parsed, GeneratedVehicleAnswer)
    assert parsed.answer == "Check the coolant level and cooling fan first."
    assert parsed.findings == ["Coolant temperature reached 108 C."]
    assert len(parsed.recommendations) == 1


def test_parser_maps_invalid_json_to_provider_error() -> None:
    with pytest.raises(InvalidModelResponseError) as error:
        VehicleAnswerParser().parse(chat_result("not-json"))

    assert error.value.code == "invalid_response"
    assert error.value.provider == "stub"
    assert error.value.model == "stub-chat"
    assert error.value.__cause__ is not None


@pytest.mark.parametrize(
    "payload",
    [
        {"findings": [], "recommendations": []},
        {"answer": "   ", "findings": [], "recommendations": []},
        {"answer": "Valid", "findings": [], "recommendations": [], "extra": True},
    ],
)
def test_parser_rejects_content_that_violates_answer_schema(payload: dict) -> None:
    with pytest.raises(InvalidModelResponseError):
        VehicleAnswerParser().parse(chat_result(json.dumps(payload)))
