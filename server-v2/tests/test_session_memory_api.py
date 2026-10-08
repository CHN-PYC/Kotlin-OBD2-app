import json
from pathlib import Path

import httpx2
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

FIXTURE = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"


def payload(question: str) -> dict:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["question"] = question
    return data


def test_second_turn_uses_memory_and_delete_clears_it() -> None:
    prompt_payloads: list[dict] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        outbound = json.loads(request.content)
        prompt_payloads.append(json.loads(outbound["messages"][1]["content"]))
        return httpx2.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "answer": "Inspect the relevant system.",
                            "findings": [],
                            "recommendations": ["Collect more evidence."],
                        }
                    ),
                },
                "done": True,
                "done_reason": "stop",
            },
        )

    outbound = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    application = create_app(
        settings=Settings(_env_file=None, ollama_chat_model="qwen3:4b"),
        client_factory=lambda: outbound,
    )

    with TestClient(application) as client:
        first = client.post("/qa/vehicle", json=payload("水温偏高怎么检查？"))
        second = client.post("/qa/vehicle", json=payload("这个还需要检查什么？"))
        cleared = client.delete("/qa/sessions/10001/memory")
        third = client.post("/qa/vehicle", json=payload("这个还需要检查什么？"))

    assert first.status_code == second.status_code == third.status_code == 200
    assert cleared.status_code == 204
    assert "ECT" in first.json()["rewritten_query"]
    assert "上一轮" in second.json()["rewritten_query"]
    assert len(prompt_payloads[1]["conversationHistory"]) == 1
    assert prompt_payloads[1]["conversationHistory"][0]["question"] == "水温偏高怎么检查？"
    assert "上一轮" not in third.json()["rewritten_query"]
    assert prompt_payloads[2]["conversationHistory"] == []
