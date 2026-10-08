from app.contracts.session_memory import SessionMemoryStore
from app.core.config import SessionMemoryProvider, Settings
from app.services.memory.in_memory import InMemorySessionMemoryStore
from app.services.memory.redis_store import RedisSessionMemoryStore


def create_session_memory_store(settings: Settings) -> SessionMemoryStore:
    if settings.session_memory_provider is SessionMemoryProvider.REDIS:
        return RedisSessionMemoryStore(
            url=settings.redis_url,
            ttl_seconds=settings.session_ttl_seconds,
            max_turns=settings.session_max_turns,
        )
    return InMemorySessionMemoryStore(max_turns=settings.session_max_turns)
