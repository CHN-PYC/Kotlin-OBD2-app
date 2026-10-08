import asyncio
import math
import time
from collections.abc import Callable
from enum import Enum
from typing import ClassVar

from app.providers.chat import ChatModel, ChatRequest, ChatResult
from app.providers.errors import ModelProviderError


class CircuitOpenError(ModelProviderError):
    code: ClassVar[str] = "circuit_open"
    retryable: ClassVar[bool] = False


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerChatModel:
    """Share one instance per application event loop, outside the retry adapter."""

    def __init__(
        self,
        delegate: ChatModel,
        *,
        failure_threshold: int = 5,
        recovery_seconds: float = 30,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if type(failure_threshold) is not int or failure_threshold < 1:
            raise ValueError("failure_threshold must be a positive integer")
        if not math.isfinite(recovery_seconds) or recovery_seconds <= 0:
            raise ValueError("recovery_seconds must be finite and positive")
        self.delegate = delegate
        self.provider_name = delegate.provider_name
        self.model_name = delegate.model_name
        self._threshold = failure_threshold
        self._recovery = recovery_seconds
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._epoch = 0

    @property
    def state(self) -> CircuitState:
        return self._state

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        self._epoch += 1

    async def generate(self, request: ChatRequest) -> ChatResult:
        # No await before admission: only one task can become the half-open probe
        # on this event loop. Other workers have their own independent breaker.
        if self._state is CircuitState.OPEN:
            if self._clock() - self._opened_at >= self._recovery:
                self._state = CircuitState.HALF_OPEN
            else:
                raise self._rejected()
        elif self._state is CircuitState.HALF_OPEN:
            raise self._rejected()
        epoch = self._epoch
        probe = self._state is CircuitState.HALF_OPEN
        try:
            result = await self.delegate.generate(request)
        except (Exception, asyncio.CancelledError) as exc:
            if epoch == self._epoch:
                if probe:
                    # A cancelled/invalid probe is not proof of recovery.
                    self._open()
                elif isinstance(exc, ModelProviderError) and exc.retryable:
                    self._failures += 1
                    if self._failures >= self._threshold:
                        self._open()
            raise
        if epoch == self._epoch:
            # Ignore late results from calls admitted before the circuit opened.
            self._state = CircuitState.CLOSED
            self._failures = 0
        return result

    def _rejected(self) -> CircuitOpenError:
        return CircuitOpenError(
            "Model circuit is open; retry after recovery interval",
            provider=self.provider_name,
            model=self.model_name,
        )
