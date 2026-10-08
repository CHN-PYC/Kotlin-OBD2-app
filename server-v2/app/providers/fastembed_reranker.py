import asyncio
from collections.abc import Callable, Iterable
from threading import Lock
from typing import Protocol

from fastembed.rerank.cross_encoder import TextCrossEncoder

from app.providers.errors import ModelServerError
from app.schemas.reranking import RerankModelResult, RerankPair


class _CrossEncoderRuntime(Protocol):
    def rerank(
        self,
        query: str,
        documents: Iterable[str],
        batch_size: int = 64,
        **kwargs: object,
    ) -> Iterable[float]: ...


RuntimeFactory = Callable[[], _CrossEncoderRuntime]


class FastEmbedCrossEncoder:
    """Lazy ONNX Cross-Encoder adapter that keeps blocking work off the event loop."""

    provider_name = "fastembed"

    def __init__(
        self,
        *,
        model_name: str,
        batch_size: int,
        threads: int | None = None,
        runtime_factory: RuntimeFactory | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name must not be blank")
        if type(batch_size) is not int or batch_size <= 0:
            raise ValueError("batch_size must be a positive integer")
        if threads is not None and (type(threads) is not int or threads <= 0):
            raise ValueError("threads must be a positive integer or None")
        self.model_name = model_name.strip()
        self._batch_size = batch_size
        self._runtime_factory = runtime_factory or (
            lambda: TextCrossEncoder(
                model_name=self.model_name,
                threads=threads,
                lazy_load=True,
            )
        )
        self._runtime: _CrossEncoderRuntime | None = None
        # Initialization and inference are synchronous. The lock prevents duplicate
        # model loads and caps this local CPU provider at one inference at a time.
        self._runtime_lock = Lock()

    async def score_pairs(self, pairs: list[RerankPair]) -> RerankModelResult:
        if not pairs:
            return RerankModelResult(
                provider=self.provider_name,
                model=self.model_name,
                scores=[],
            )
        query = pairs[0].query_text
        if any(pair.query_text != query for pair in pairs):
            raise ValueError("FastEmbed batch requires one shared query")
        try:
            scores = await asyncio.to_thread(
                self._score_sync,
                query,
                [pair.document_text for pair in pairs],
            )
        except (OSError, RuntimeError, ValueError) as exc:
            raise ModelServerError(
                "Local reranker inference failed",
                provider=self.provider_name,
                model=self.model_name,
            ) from exc
        return RerankModelResult(
            provider=self.provider_name,
            model=self.model_name,
            scores=scores,
        )

    def _score_sync(self, query: str, documents: list[str]) -> list[float]:
        with self._runtime_lock:
            if self._runtime is None:
                self._runtime = self._runtime_factory()
            return [
                float(score)
                for score in self._runtime.rerank(
                    query,
                    documents,
                    batch_size=self._batch_size,
                )
            ]
