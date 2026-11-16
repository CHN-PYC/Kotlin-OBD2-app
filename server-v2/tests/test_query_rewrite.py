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


def test_resolves_reference_from_raw_question_not_derived_query() -> None:
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

    assert result.rewritten_query.startswith("这个怎么检查？")
    assert "P0171 是什么？" in result.rewritten_query
    assert "混合气过稀诊断" not in result.rewritten_query
    assert "resolve_previous_turn_reference" in result.applied_rules


def turn(question: str, rewritten_query: str | None = None) -> ConversationTurn:
    return ConversationTurn(
        question=question,
        rewritten_query=(rewritten_query or question)[:500],
        answer="已回答。",
        answer_mode=AnswerMode.LLM_RAG,
        created_at=1,
    )


def test_chained_follow_ups_do_not_grow_and_keep_current_question() -> None:
    rewriter = DeterministicQueryRewriter()
    memory = SessionMemory(session_id="s1", turns=[turn("P0171 混合气过稀怎么诊断？")])
    lengths: list[int] = []
    for question in ["这个呢？", "还是这样怎么办", "它严重吗", "那个要换吗", "这种情况能开吗"]:
        result = rewriter.rewrite(request(question), memory)
        assert result.rewritten_query.startswith(question)
        assert "P0171 混合气过稀怎么诊断？" in result.rewritten_query
        assert result.rewritten_query.count("上文话题") == 1
        lengths.append(len(result.rewritten_query))
        memory.turns.append(turn(question, result.rewritten_query))
        memory.turns[:] = memory.turns[-10:]

    assert max(lengths) - min(lengths) < 20


def test_self_contained_question_switches_topic_without_history() -> None:
    memory = SessionMemory(session_id="s1", turns=[turn("P0171 混合气过稀怎么诊断？")])

    result = DeterministicQueryRewriter().rewrite(request("蓄电池电压多少算正常？"), memory)

    assert "P0171" not in result.rewritten_query
    assert "resolve_previous_turn_reference" not in result.applied_rules


def test_long_history_is_truncated_before_current_question() -> None:
    long_topic = "P0300 " + "发动机抖动并且怠速不稳" * 60
    memory = SessionMemory(session_id="s1", turns=[turn(long_topic[:1000])])

    result = DeterministicQueryRewriter().rewrite(request("这个怎么检查？"), memory)

    assert len(result.rewritten_query) <= 500
    assert result.rewritten_query.startswith("这个怎么检查？")
    assert "P0300" in result.rewritten_query


def test_overlong_current_question_is_bounded() -> None:
    result = DeterministicQueryRewriter().rewrite(
        request("水温" + "偏高" * 400),
        SessionMemory(session_id="s1"),
    )

    assert len(result.rewritten_query) == 500
    assert result.rewritten_query.startswith("水温偏高")
