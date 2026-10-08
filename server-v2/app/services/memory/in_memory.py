from app.schemas.memory import ConversationTurn, SessionMemory


class InMemorySessionMemoryStore:
    """Process-local test/development store; data disappears on restart."""

    def __init__(self, *, max_turns: int = 10) -> None:
        if type(max_turns) is not int or max_turns <= 0:
            raise ValueError("max_turns must be a positive integer")
        self._max_turns = max_turns
        self._turns: dict[str, list[ConversationTurn]] = {}

    async def load(self, session_id: str) -> SessionMemory:
        return SessionMemory(
            session_id=session_id,
            turns=[turn.model_copy(deep=True) for turn in self._turns.get(session_id, [])],
        )

    async def append(self, session_id: str, turn: ConversationTurn) -> None:
        turns = self._turns.setdefault(session_id, [])
        turns.append(turn.model_copy(deep=True))
        del turns[: -self._max_turns]

    async def clear(self, session_id: str) -> None:
        self._turns.pop(session_id, None)

    async def aclose(self) -> None:
        return None
