from typing import Protocol

from app.schemas.retrieval import RetrievedSource
from app.schemas.vector_store import VectorRecord


class VectorStore(Protocol):
    async def upsert(self, records: list[VectorRecord]) -> None: ...

    async def search(self, query_vector: list[float], *, k: int) -> list[RetrievedSource]: ...

    async def delete(self, chunk_ids: list[str]) -> None: ...

    async def aclose(self) -> None: ...
