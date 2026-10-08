import json

import httpx2
import pytest

from app.core.config import Settings
from app.schemas.generation import GeneratedVehicleAnswer
from scripts import profile_ollama


@pytest.mark.parametrize("structured", [False, True])
def test_profile_sends_schema_only_when_enabled(monkeypatch, capsys, structured: bool) -> None:
    captured = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured.append(json.loads(request.content))
        return httpx2.Response(
            200,
            json={
                "done_reason": "stop",
                "message": {"content": '{"answer":"Inspect the cooling system."}'},
            },
        )

    real_client = httpx2.Client
    monkeypatch.setattr(
        profile_ollama.httpx2,
        "Client",
        lambda **kwargs: real_client(
            transport=httpx2.MockTransport(handler),
            **kwargs,
        ),
    )
    monkeypatch.setattr(
        profile_ollama,
        "Settings",
        lambda: Settings(
            _env_file=None,
            ollama_chat_model="qwen3:4b",
            ollama_base_url="http://127.0.0.1:11434",
        ),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["profile", "--case", "vehicle", "--tokens", "256"]
        + (["--structured"] if structured else []),
    )
    assert profile_ollama.main() == 0
    payload = captured[0]
    if structured:
        assert payload["format"] == GeneratedVehicleAnswer.model_json_schema()
    else:
        assert "format" not in payload
    assert json.loads(capsys.readouterr().out)["accepted"] is True
