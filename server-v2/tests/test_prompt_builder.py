import json
from pathlib import Path

from app.providers.chat import ChatOptions, ChatRole
from app.schemas.qa import VehicleQARequest
from app.services.generation.prompt_builder import VehicleQAPromptBuilder

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"


def load_request() -> VehicleQARequest:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return VehicleQARequest.model_validate(payload)


def test_builds_grounded_chat_request_from_vehicle_request() -> None:
    chat_request = VehicleQAPromptBuilder().build(load_request())

    assert [message.role for message in chat_request.messages] == [
        ChatRole.SYSTEM,
        ChatRole.USER,
    ]
    system_prompt = chat_request.messages[0].content.lower()
    assert "provided evidence" in system_prompt
    assert "evidence is insufficient" in system_prompt
    assert "do not claim" in system_prompt
    assert "json object" in system_prompt
    assert '"answer"' in system_prompt
    assert '"findings"' in system_prompt
    assert '"recommendations"' in system_prompt
    assert "arrays of strings" in system_prompt
    assert "never arrays of objects" in system_prompt
    assert chat_request.options.temperature == 0.0
    assert chat_request.options.max_output_tokens == 512

    prompt_data = json.loads(chat_request.messages[1].content)
    assert prompt_data["question"] == "车辆行驶过程中水温偏高，应该优先检查什么？"
    assert prompt_data["vehicleContext"]["sessionSummary"]["maxCoolantTemp"] == 108
    assert prompt_data["ruleSummary"]["findings"][0]["code"] == "COOLANT_HIGH"
    assert "sessionId" not in prompt_data
    assert "topK" not in prompt_data


def test_builds_prompt_when_rule_summary_is_missing() -> None:
    request = load_request().model_copy(update={"rule_summary": None})

    chat_request = VehicleQAPromptBuilder().build(request)

    prompt_data = json.loads(chat_request.messages[1].content)
    assert prompt_data["ruleSummary"] is None
    assert prompt_data["vehicleContext"]["promptHints"]["instruction"]


def test_build_uses_configured_output_budget_with_independent_options() -> None:
    options = ChatOptions(max_output_tokens=2048)
    builder = VehicleQAPromptBuilder(options=options)
    result = builder.build(load_request())
    assert result.options.max_output_tokens == 2048
    assert result.options is not options
