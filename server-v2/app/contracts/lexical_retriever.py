from typing import Protocol

from app.schemas.retrieval import RetrievedSource


class LexicalRetriever(Protocol):
    async def search(self, query_text: str, *, k: int) -> list[RetrievedSource]: ...
