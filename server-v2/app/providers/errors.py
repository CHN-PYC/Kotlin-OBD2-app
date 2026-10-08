from typing import ClassVar


class ModelProviderError(Exception):
    # LEARNING: ClassVar 是类级常量，类似 Java static final，不属于实例字段。
    code: ClassVar[str] = "provider_error"
    retryable: ClassVar[bool] = False

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        model: str | None = None,
    ) -> None:
        self.message = message
        self.provider = provider
        self.model = model
        super().__init__(message)

    def __str__(self) -> str:
        model = self.model or "unconfigured"
        return f"[{self.code}] {self.provider}/{model}: {self.message}"


class ModelNotConfiguredError(ModelProviderError):
    code: ClassVar[str] = "not_configured"
    retryable: ClassVar[bool] = False


class ModelTimeoutError(ModelProviderError):
    code: ClassVar[str] = "timeout"
    retryable: ClassVar[bool] = True


class ModelConnectionError(ModelProviderError):
    code: ClassVar[str] = "connection_error"
    retryable: ClassVar[bool] = True


class InvalidModelResponseError(ModelProviderError):
    code: ClassVar[str] = "invalid_response"
    retryable: ClassVar[bool] = False


class ModelRequestError(ModelProviderError):
    code: ClassVar[str] = "request_error"
    retryable: ClassVar[bool] = False


class ModelServerError(ModelProviderError):
    code: ClassVar[str] = "server_error"
    retryable: ClassVar[bool] = True


class ModelRateLimitError(ModelProviderError):
    code: ClassVar[str] = "rate_limited"
    retryable: ClassVar[bool] = True
