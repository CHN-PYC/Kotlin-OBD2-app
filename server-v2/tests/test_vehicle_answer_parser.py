import json

import pytest

from app.providers.chat import ChatResult
from app.providers.errors import InvalidModelResponseError
from app.schemas.generation import ClaimKind, GeneratedVehicleAnswer
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
            "claims": [
                {
                    "text": "Coolant temperature reached 108 C.",
                    "kind": "cause",
                    "source_chunk_ids": [],
                },
                {
                    "text": "Stop safely if the temperature continues to rise.",
                    "kind": "check",
                    "source_chunk_ids": [],
                },
            ],
        }
    )

    parsed = VehicleAnswerParser().parse(chat_result(content))

    assert isinstance(parsed, GeneratedVehicleAnswer)
    assert parsed.answer == "Check the coolant level and cooling fan first."
    assert [claim.text for claim in parsed.claims] == [
        "Coolant temperature reached 108 C.",
        "Stop safely if the temperature continues to rise.",
    ]
    assert [claim.kind for claim in parsed.claims] == [ClaimKind.CAUSE, ClaimKind.CHECK]


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
        {"claims": []},
        {"answer": "   ", "claims": []},
        {"answer": "Valid", "claims": [], "extra": True},
        {"answer": "Valid", "findings": ["legacy field"]},
        {"answer": "Valid", "claims": [{"text": "x", "kind": "guess"}]},
        {
            "answer": "Valid",
            "claims": [{"text": "x", "kind": "cause", "source_chunk_ids": ["a", "b", "c", "d"]}],
        },
    ],
)
def test_parser_rejects_content_that_violates_answer_schema(payload: dict) -> None:
    with pytest.raises(InvalidModelResponseError):
        VehicleAnswerParser().parse(chat_result(json.dumps(payload)))
