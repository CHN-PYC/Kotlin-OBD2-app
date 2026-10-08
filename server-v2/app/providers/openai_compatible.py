import math
from typing import Any, ClassVar, Literal

import httpx2
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr

from app.providers.chat import ChatModel, ChatRequest, ChatResult
from app.providers.errors import (
    InvalidModelResponseError,
    ModelConnectionError,
    ModelNotConfiguredError,
    ModelRateLimitError,
    ModelRequestError,
    ModelServerError,
    ModelTimeoutError,
)


class _Message(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    role: Literal["assistant"]
    content: str = Field(min_length=1)


class _Choice(BaseModel):
    message: _Message
    finish_reason: str = Field(min_length=1)


class _Usage(BaseModel):
    prompt_tokens: int = Field(ge=0, strict=True)
    completion_tokens: int = Field(ge=0, strict=True)


class _Completion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    model: str = Field(min_length=1)
    choices: list[_Choice] = Field(min_length=1, max_length=1)
    usage: _Usage | None = None


class OpenAICompatibleChatModel(ChatModel):
    provider_name: ClassVar[str] = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str | None,
        model_name: str | None,
        api_key: SecretStr | None,
        timeout_seconds: float,
        json_mode: bool = False,
        client: httpx2.AsyncClient | None = None,
    ) -> None:
        if (
            not base_url
            or not model_name
            or not model_name.strip()
            or (api_key is None or not api_key.get_secret_value().strip())
        ):
            raise ModelNotConfiguredError(
                "Remote base URL, model and API key are required",
                provider=self.provider_name,
            )
        url = AnyHttpUrl(base_url)
        if url.username or url.password or url.query or url.fragment:
            raise ValueError("Remote base URL must not contain credentials, query or fragment")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        self._chat_url = f"{str(url).rstrip('/')}/chat/completions"
        self._model_name = model_name.strip()
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._json_mode = json_mode
        self._owns_client = client is None
        self._client = client if client is not None else httpx2.AsyncClient()

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, request: ChatRequest) -> ChatResult:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [message.model_dump(mode="json") for message in request.messages],
            "stream": False,
            "temperature": request.options.temperature,
            "max_tokens": request.options.max_output_tokens,
        }
        if self._json_mode:
            # LEARNING: JSON mode 约束格式，不保证诊断事实正确，仍需 Parser 校验。
            payload["response_format"] = {"type": "json_object"}
        try:
            response = await self._client.post(
                self._chat_url,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key.get_secret_value()}"},
                timeout=self._timeout,
                follow_redirects=False,
            )
            response.raise_for_status()
        except httpx2.TimeoutException as exc:
            raise ModelTimeoutError(
                "Remote model timed out", provider=self.provider_name, model=self.model_name
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
            # LEARNING: 不把服务商原始 body 或密钥放进对外错误、trace。
            raise error_type(
                f"Remote model returned HTTP {status}",
                provider=self.provider_name,
                model=self.model_name,
            ) from exc
        except httpx2.RequestError as exc:
            raise ModelConnectionError(
                "Remote model connection failed", provider=self.provider_name, model=self.model_name
            ) from exc
        try:
            parsed = _Completion.model_validate(response.json())
        except ValueError as exc:
            raise InvalidModelResponseError(
                "Remote model returned invalid completion data",
                provider=self.provider_name,
                model=self.model_name,
            ) from exc
        choice = parsed.choices[0]
        return ChatResult(
            content=choice.message.content,
            provider=self.provider_name,
            model=parsed.model,
            finish_reason=choice.finish_reason,
            # Existing ChatResult requires integers; missing usage is not a real measured zero.
            input_tokens=parsed.usage.prompt_tokens if parsed.usage else 0,
            output_tokens=parsed.usage.completion_tokens if parsed.usage else 0,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
