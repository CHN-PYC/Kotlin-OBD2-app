from app.services.llm_service import LlmService


def test_parse_response_handles_valid_json():
    service = LlmService()
    result = service._parse_response(
        '{"severity":"WARNING","answer":"Coolant is high","findings":["coolant elevated"],"recommendations":["check fan"]}',
        '{"raw":true}',
        [],
    )
    assert result["severity"] == "WARNING"
    assert result["answer"] == "Coolant is high"
    assert result["findings"] == ["coolant elevated"]
    assert result["recommendations"] == ["check fan"]


def test_parse_response_falls_back_on_plain_text():
    service = LlmService()
    result = service._parse_response(
        'plain text answer without json',
        'plain text answer without json',
        [],
    )
    assert result["severity"] == "NOTICE"
    assert "plain text answer" in result["answer"]
    assert result["findings"]
