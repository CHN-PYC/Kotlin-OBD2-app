import asyncio

from app.schemas.memory import ConversationTurn
from app.schemas.qa import AnswerMode
from app.services.memory.in_memory import InMemorySessionMemoryStore


def turn(index: int) -> ConversationTurn:
    return ConversationTurn(
        question=f"question {index}",
        rewritten_query=f"query {index}",
        answer=f"answer {index}",
        answer_mode=AnswerMode.LLM_RAG,
        created_at=index,
    )


def test_memory_is_session_isolated_bounded_and_clearable() -> None:
    async def scenario() -> None:
        store = InMemorySessionMemoryStore(max_turns=2)
        for index in range(3):
            await store.append("session-a", turn(index))
        await store.append("session-b", turn(9))

        assert [item.created_at for item in (await store.load("session-a")).turns] == [1, 2]
        assert [item.created_at for item in (await store.load("session-b")).turns] == [9]

        await store.clear("session-a")
        assert (await store.load("session-a")).turns == []

    asyncio.run(scenario())
