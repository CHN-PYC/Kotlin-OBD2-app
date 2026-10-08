from typing import Protocol, runtime_checkable

from app.schemas.reranking import RerankModelResult, RerankPair


@runtime_checkable
class CrossEncoderModel(Protocol):
    """Provider boundary for scoring query-document text pairs in one batch."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    async def score_pairs(self, pairs: list[RerankPair]) -> RerankModelResult: ...
