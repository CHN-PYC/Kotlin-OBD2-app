import json
from pathlib import Path

from app.schemas.memory import ConversationTurn, SessionMemory
from app.schemas.qa import AnswerMode, VehicleQARequest
from app.services.retrieval.query_rewrite import DeterministicQueryRewriter

FIXTURE = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"


def request(question: str) -> VehicleQARequest:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["question"] = question
    return VehicleQARequest.model_validate(payload)


def test_normalizes_vehicle_terms_without_calling_a_model() -> None:
    result = DeterministicQueryRewriter().rewrite(
        request("水温偏高并且空气流量计异常怎么检查？"),
        SessionMemory(session_id="s1"),
    )

    assert "ECT" in result.rewritten_query
    assert "MAF" in result.rewritten_query
    assert result.applied_rules == ["normalize_vehicle_terms"]


def test_resolves_reference_from_latest_turn_only() -> None:
    memory = SessionMemory(
        session_id="s1",
        turns=[
            ConversationTurn(
                question="P0171 是什么？",
                rewritten_query="P0171 混合气过稀诊断",
                answer="需要检查燃油修正。",
                answer_mode=AnswerMode.LLM_RAG,
                created_at=1,
            )
        ],
    )

    result = DeterministicQueryRewriter().rewrite(request("这个怎么检查？"), memory)

    assert "P0171 混合气过稀诊断" in result.rewritten_query
    assert "resolve_previous_turn_reference" in result.applied_rules
