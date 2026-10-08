from typing import Any, ClassVar

import httpx2
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.providers.chat import ChatModel, ChatRequest, ChatResult
from app.providers.errors import (
    InvalidModelResponseError,
    ModelConnectionError,
    ModelNotConfiguredError,
    ModelRequestError,
    ModelServerError,
    ModelTimeoutError,
)


class _OllamaMessage(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    content: str = Field(min_length=1)


class _OllamaChatResponse(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    model: str = Field(min_length=1)
    message: _OllamaMessage
    done: bool
    done_reason: str = Field(default="unknown", min_length=1)
    prompt_eval_count: int = Field(default=0, ge=0)
    eval_count: int = Field(default=0, ge=0)


class OllamaChatModel(ChatModel):
    provider_name: ClassVar[str] = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model_name: str | None,
        timeout_seconds: float,
        client: httpx2.AsyncClient | None = None,
    ) -> None:
        if model_name is None or not model_name.strip():
            raise ModelNotConfiguredError(
                "chat model is not configured",
                provider=self.provider_name,
            )
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        self._chat_url = f"{base_url.rstrip('/')}/api/chat"
        self._model_name = model_name.strip()
        self.timeout_seconds = timeout_seconds
        self._client = client or httpx2.AsyncClient()
        # LEARNING: 谁创建资源谁关闭；外部注入的共享 client 由 FastAPI lifespan 管理。
        self._owns_client = client is None

    @property
    def model_name(self) -> str:
        return self._model_name

    def _build_payload(self, request: ChatRequest) -> dict[str, Any]:
        return {
            "model": self.model_name,
            "messages": [message.model_dump(mode="json") for message in request.messages],
            "stream": False,
            "think": False,
            "options": {
                "temperature": request.options.temperature,
                "num_predict": request.options.max_output_tokens,
            },
        }

    async def generate(self, request: ChatRequest) -> ChatResult:
        try:
            response = await self._client.post(
                self._chat_url,
                json=self._build_payload(request),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx2.TimeoutException as exc:
            raise ModelTimeoutError(
                "model request timed out",
                provider=self.provider_name,
                model=self.model_name,
            ) from exc
        except httpx2.ConnectError as exc:
            raise ModelConnectionError(
                "could not connect to model provider",
                provider=self.provider_name,
                model=self.model_name,
            ) from exc
        except httpx2.HTTPStatusError as exc:
            # LEARNING: 5xx 通常是暂态服务故障；4xx 多为请求问题，盲目重试无效。
            error_type = ModelServerError if exc.response.status_code >= 500 else ModelRequestError
            raise error_type(
                f"model provider returned HTTP {exc.response.status_code}",
                provider=self.provider_name,
                model=self.model_name,
            ) from exc
        except httpx2.RequestError as exc:
            raise ModelConnectionError(
                "model provider request failed",
                provider=self.provider_name,
                model=self.model_name,
            ) from exc

        try:
            parsed = _OllamaChatResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise InvalidModelResponseError(
                "model provider returned an invalid response",
                provider=self.provider_name,
                model=self.model_name,
            ) from exc

        return ChatResult(
            content=parsed.message.content,
            provider=self.provider_name,
            model=parsed.model,
            finish_reason=parsed.done_reason,
            input_tokens=parsed.prompt_eval_count,
            output_tokens=parsed.eval_count,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
