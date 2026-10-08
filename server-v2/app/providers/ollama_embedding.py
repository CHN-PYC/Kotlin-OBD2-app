import math
from typing import ClassVar

import httpx2
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.providers.embedding import EmbeddingRequest, EmbeddingResult, EmbeddingVector
from app.providers.errors import (
    InvalidModelResponseError,
    ModelConnectionError,
    ModelNotConfiguredError,
    ModelRateLimitError,
    ModelRequestError,
    ModelServerError,
    ModelTimeoutError,
)
from app.services.retrieval.embedding_validation import validate_embedding_result


class _OllamaEmbedResponse(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")
    model: str = Field(min_length=1)
    embeddings: list[EmbeddingVector] = Field(min_length=1)


def _canonical_model(name: str) -> str:
    # Only the final path component contains the model tag; a registry may have a port.
    return name if ":" in name.rsplit("/", 1)[-1] else f"{name}:latest"


class OllamaEmbeddingModel:
    provider_name: ClassVar[str] = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model_name: str | None,
        expected_dimension: int,
        timeout_seconds: float,
        num_gpu: int | None = None,
        client: httpx2.AsyncClient | None = None,
    ) -> None:
        if model_name is None or not model_name.strip():
            raise ModelNotConfiguredError("Embedding model is not configured", provider="ollama")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        if type(expected_dimension) is not int or expected_dimension <= 0:
            raise ValueError("expected_dimension must be a positive integer")
        if num_gpu is not None and (type(num_gpu) is not int or num_gpu < 0):
            raise ValueError("num_gpu must be a non-negative integer or None")
        url = AnyHttpUrl(base_url)
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("Base URL must not contain credentials, query or fragment")
        self._embed_url = f"{str(url).rstrip('/')}/api/embed"
        self.model_name = model_name.strip()
        self._expected_dimension = expected_dimension
        self._timeout = timeout_seconds
        self._num_gpu = num_gpu
        self._owns_client = client is None
        self._client = client if client is not None else httpx2.AsyncClient()

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        response = await self._send(request)
        try:
            parsed = _OllamaEmbedResponse.model_validate(response.json())
        except ValueError as exc:
            raise InvalidModelResponseError(
                "Ollama returned invalid embedding data", provider="ollama", model=self.model_name
            ) from exc
        if _canonical_model(parsed.model) != _canonical_model(self.model_name):
            raise InvalidModelResponseError(
                "Ollama returned a different embedding model",
                provider="ollama",
                model=self.model_name,
            )
        result = EmbeddingResult(
            provider=self.provider_name, model=parsed.model, vectors=parsed.embeddings
        )
        return validate_embedding_result(
            request, result, expected_dimension=self._expected_dimension
        )

    async def _send(self, request: EmbeddingRequest) -> httpx2.Response:
        payload: dict[str, object] = {
            "model": self.model_name,
            "input": request.texts,
            "truncate": False,
        }
        if self._num_gpu is not None:
            # LEARNING: this is a hardware compatibility control, not retrieval tuning.
            # num_gpu=0 avoids NaN/OOM failures observed on low-VRAM GPUs.
            payload["options"] = {"num_gpu": self._num_gpu}
        try:
            response = await self._client.post(
                self._embed_url,
                json=payload,
                timeout=self._timeout,
                follow_redirects=False,
            )
            response.raise_for_status()
            return response
        except httpx2.TimeoutException as exc:
            raise ModelTimeoutError(
                "Embedding request timed out", provider="ollama", model=self.model_name
            ) from exc
        except httpx2.HTTPStatusError as exc:
            status = exc.response.status_code
            error_type = (
                ModelRateLimitError
                if status == 429
                else ModelServerError
                if status >= 500
                else ModelRequestError
            )
            # Do not expose remote response bodies, which may contain input text.
            raise error_type(
                f"Ollama embedding returned HTTP {status}", provider="ollama", model=self.model_name
            ) from exc
        except httpx2.RequestError as exc:
            raise ModelConnectionError(
                "Ollama embedding connection failed", provider="ollama", model=self.model_name
            ) from exc

    async def aclose(self) -> None:
        # A shared client belongs to its caller, just like the existing chat provider.
        if self._owns_client:
            await self._client.aclose()
