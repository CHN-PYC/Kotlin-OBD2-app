from pathlib import Path

from app.schemas.memory import ConversationTurn
from app.schemas.qa import AnswerMode, VehicleQARequest
from app.schemas.retrieval import RetrievedSource
from app.services.generation.context_manager import ContextWindowManager

FIXTURE = Path(__file__).parent / "fixtures" / "vehicle_qa_request.json"


def request() -> VehicleQARequest:
    return VehicleQARequest.model_validate_json(FIXTURE.read_text(encoding="utf-8"))


def source(chunk_id: str, text: str) -> RetrievedSource:
    return RetrievedSource(
        chunk_id=chunk_id,
        doc_id="doc",
        title="Guide",
        score=0.8,
        text=text,
    )


def turn(index: int, answer: str = "answer") -> ConversationTurn:
    return ConversationTurn(
        question=f"question {index}",
        rewritten_query=f"query {index}",
        answer=answer,
        answer_mode=AnswerMode.LLM_RAG,
        created_at=index,
    )


def test_prioritizes_complete_evidence_then_most_recent_history() -> None:
    manager = ContextWindowManager(max_characters=2500, max_history_turns=2)
    selection = manager.select(
        request(),
        rewritten_query="coolant ECT checks",
        sources=[source("a", "A" * 250), source("b", "B" * 2000)],
        history=[turn(1), turn(2), turn(3)],
    )

    assert [item.chunk_id for item in selection.sources] == ["a"]
    assert [item.created_at for item in selection.history] == [2, 3]
    assert selection.estimated_characters <= 2500


def test_does_not_split_oversized_evidence_chunk() -> None:
    selection = ContextWindowManager(max_characters=2000).select(
        request(),
        rewritten_query="query",
        sources=[source("huge", "X" * 10000)],
        history=[],
    )

    assert selection.sources == []


def test_zero_history_limit_excludes_all_turns() -> None:
    selection = ContextWindowManager(max_history_turns=0).select(
        request(),
        rewritten_query="query",
        sources=[],
        history=[turn(1)],
    )
    assert selection.history == []
