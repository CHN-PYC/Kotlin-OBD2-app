from collections.abc import Awaitable
from hashlib import sha256
from typing import Any, cast

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.schemas.memory import ConversationTurn, SessionMemory
from app.services.memory.errors import SessionMemoryError


class RedisSessionMemoryStore:
    """Bounded Redis-list memory with atomic append, trim, and TTL refresh."""

    def __init__(
        self,
        *,
        url: str,
        ttl_seconds: int,
        max_turns: int,
        key_prefix: str = "vehicle-agent:session",
        client: Redis | None = None,
    ) -> None:
        if ttl_seconds <= 0 or max_turns <= 0:
            raise ValueError("ttl_seconds and max_turns must be positive")
        self._ttl_seconds = ttl_seconds
        self._max_turns = max_turns
        self._key_prefix = key_prefix
        self._client = client or Redis.from_url(url, decode_responses=True)
        self._owns_client = client is None

    def _key(self, session_id: str) -> str:
        digest = sha256(session_id.encode("utf-8")).hexdigest()
        return f"{self._key_prefix}:{digest}"

    async def load(self, session_id: str) -> SessionMemory:
        try:
            values = await cast(
                Awaitable[list[Any]],
                self._client.lrange(self._key(session_id), 0, -1),
            )
            turns = [ConversationTurn.model_validate_json(value) for value in values]
        except (RedisError, ValidationError, TypeError) as exc:
            raise SessionMemoryError("failed to load session memory") from exc
        return SessionMemory(session_id=session_id, turns=turns)

    async def append(self, session_id: str, turn: ConversationTurn) -> None:
        try:
            pipeline = self._client.pipeline(transaction=True)
            pipeline.rpush(self._key(session_id), turn.model_dump_json())
            pipeline.ltrim(self._key(session_id), -self._max_turns, -1)
            pipeline.expire(self._key(session_id), self._ttl_seconds)
            await pipeline.execute()
        except RedisError as exc:
            raise SessionMemoryError("failed to append session memory") from exc

    async def clear(self, session_id: str) -> None:
        try:
            await self._client.delete(self._key(session_id))
        except RedisError as exc:
            raise SessionMemoryError("failed to clear session memory") from exc

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
