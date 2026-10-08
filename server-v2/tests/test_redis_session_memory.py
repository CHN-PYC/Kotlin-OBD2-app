import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from redis.exceptions import ConnectionError

from app.schemas.memory import ConversationTurn
from app.schemas.qa import AnswerMode
from app.services.memory.errors import SessionMemoryError
from app.services.memory.redis_store import RedisSessionMemoryStore


def turn() -> ConversationTurn:
    return ConversationTurn(
        question="这个怎么检查？",
        rewritten_query="P0171 混合气过稀怎么检查？",
        answer="检查燃油修正和进气泄漏。",
        answer_mode=AnswerMode.LLM_RAG,
        created_at=1,
    )


def test_redis_store_uses_transactional_append_trim_and_expire() -> None:
    pipeline = Mock()
    pipeline.rpush.return_value = pipeline
    pipeline.ltrim.return_value = pipeline
    pipeline.expire.return_value = pipeline
    pipeline.execute = AsyncMock(return_value=[1, True, True])
    client = Mock()
    client.pipeline.return_value = pipeline
    client.lrange = AsyncMock(return_value=[turn().model_dump_json()])
    client.delete = AsyncMock(return_value=1)
    store = RedisSessionMemoryStore(
        url="redis://localhost",
        ttl_seconds=1800,
        max_turns=10,
        client=client,  # type: ignore[arg-type]
    )

    async def scenario() -> None:
        await store.append("private-session-id", turn())
        loaded = await store.load("private-session-id")
        await store.clear("private-session-id")
        assert loaded.turns == [turn()]

    asyncio.run(scenario())

    key = pipeline.rpush.call_args.args[0]
    assert key.startswith("vehicle-agent:session:")
    assert "private-session-id" not in key
    pipeline.ltrim.assert_called_once_with(key, -10, -1)
    pipeline.expire.assert_called_once_with(key, 1800)
    pipeline.execute.assert_awaited_once()


def test_redis_store_maps_connection_failure_without_leaking_session_id() -> None:
    client = Mock()
    client.lrange = AsyncMock(side_effect=ConnectionError("down"))
    store = RedisSessionMemoryStore(
        url="redis://localhost",
        ttl_seconds=1800,
        max_turns=10,
        client=client,  # type: ignore[arg-type]
    )

    with pytest.raises(SessionMemoryError) as captured:
        asyncio.run(store.load("secret-session"))

    assert "secret-session" not in str(captured.value)
