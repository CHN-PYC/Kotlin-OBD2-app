import json
from dataclasses import dataclass

from app.schemas.memory import ConversationTurn
from app.schemas.qa import VehicleQARequest
from app.schemas.retrieval import RetrievedSource


class ContextBudgetExceededError(ValueError):
    pass


@dataclass(frozen=True)
class ContextSelection:
    sources: list[RetrievedSource]
    history: list[ConversationTurn]
    estimated_characters: int


class ContextWindowManager:
    """Select complete context units; never cut a JSON object or evidence chunk in half."""

    def __init__(self, *, max_characters: int = 16000, max_history_turns: int = 6) -> None:
        if max_characters < 2000 or max_history_turns < 0:
            raise ValueError("invalid context limits")
        self._max_characters = max_characters
        self._max_history_turns = max_history_turns

    def select(
        self,
        request: VehicleQARequest,
        *,
        rewritten_query: str,
        sources: list[RetrievedSource],
        history: list[ConversationTurn],
    ) -> ContextSelection:
        mandatory = {
            "question": request.question,
            "rewrittenQuery": rewritten_query,
            "vehicleContext": request.vehicle_context.model_dump(mode="json", by_alias=True),
            "ruleSummary": request.rule_summary.model_dump(mode="json", by_alias=True)
            if request.rule_summary is not None
            else None,
        }
        used = self._size(mandatory)
        if used > self._max_characters:
            raise ContextBudgetExceededError("mandatory vehicle context exceeds budget")

        selected_sources: list[RetrievedSource] = []
        for source in sources:
            size = self._size(source.model_dump(mode="json"))
            if used + size <= self._max_characters:
                selected_sources.append(source.model_copy(deep=True))
                used += size

        selected_history_reversed: list[ConversationTurn] = []
        # history[-0:] means ALL history in Python; zero must disable it explicitly.
        recent = history[-self._max_history_turns :] if self._max_history_turns else []
        for turn in reversed(recent):
            size = self._size(self._history_payload(turn))
            if used + size <= self._max_characters:
                selected_history_reversed.append(turn.model_copy(deep=True))
                used += size

        return ContextSelection(
            sources=selected_sources,
            history=list(reversed(selected_history_reversed)),
            estimated_characters=used,
        )

    @staticmethod
    def _history_payload(turn: ConversationTurn) -> dict[str, str]:
        return {
            "question": turn.question,
            "rewrittenQuery": turn.rewritten_query,
            "answer": turn.answer,
            "answerMode": turn.answer_mode.value,
        }

    @staticmethod
    def _size(value: object) -> int:
        return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
