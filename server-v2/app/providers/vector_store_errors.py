from typing import ClassVar


class VectorStoreProviderError(Exception):
    code: ClassVar[str] = "vector_store_error"
    retryable: ClassVar[bool] = False

    def __init__(self, message: str, *, operation: str, collection: str) -> None:
        self.message = message
        self.operation = operation
        self.collection = collection
        super().__init__(message)

    def __str__(self) -> str:
        return f"[{self.code}] qdrant/{self.collection}/{self.operation}: {self.message}"


class VectorStoreTimeoutError(VectorStoreProviderError):
    code = "timeout"
    retryable = True


class VectorStoreConnectionError(VectorStoreProviderError):
    code = "connection_error"
    retryable = True


class VectorStoreAuthenticationError(VectorStoreProviderError):
    code = "authentication_error"


class VectorStoreRateLimitError(VectorStoreProviderError):
    code = "rate_limited"
    retryable = True


class VectorStoreRequestError(VectorStoreProviderError):
    code = "request_error"


class VectorStoreServerError(VectorStoreProviderError):
    code = "server_error"
    retryable = True


class VectorStoreInvalidResponseError(VectorStoreProviderError):
    code = "invalid_response"


class VectorStoreConfigurationError(VectorStoreProviderError, ValueError):
    code = "configuration_error"
