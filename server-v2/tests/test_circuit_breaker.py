import asyncio

import pytest

from app.providers.chat import ChatMessage, ChatRequest, ChatResult
from app.providers.circuit_breaker import (
    CircuitBreakerChatModel,
    CircuitOpenError,
    CircuitState,
)
from app.providers.errors import ModelRequestError, ModelServerError

REQUEST = ChatRequest(messages=[ChatMessage(role="user", content="question")])
RESULT = ChatResult(
    content="answer",
    provider="fake",
    model="fake",
    finish_reason="stop",
    input_tokens=1,
    output_tokens=1,
)


class Model:
    provider_name = "fake"
    model_name = "fake"

    def __init__(self) -> None:
        self.calls = 0
        self.error: Exception | None = None
        self.release: asyncio.Event | None = None
        self.entered = asyncio.Event()

    async def generate(self, request: ChatRequest) -> ChatResult:
        self.calls += 1
        self.entered.set()
        if self.release is not None:
            await self.release.wait()
        if self.error is not None:
            raise self.error
        return RESULT


def test_opens_after_threshold_and_recovers_after_cooldown() -> None:
    async def run() -> None:
        now = [0.0]
        model = Model()
        breaker = CircuitBreakerChatModel(
            model,
            failure_threshold=2,
            recovery_seconds=10,
            clock=lambda: now[0],
        )
        model.error = ModelServerError("down", provider="fake")
        for _ in range(2):
            with pytest.raises(ModelServerError):
                await breaker.generate(REQUEST)
        assert breaker.state is CircuitState.OPEN
        with pytest.raises(CircuitOpenError):
            await breaker.generate(REQUEST)
        assert model.calls == 2
        now[0] = 10
        model.error = None
        assert await breaker.generate(REQUEST) == RESULT
        assert breaker.state is CircuitState.CLOSED

    asyncio.run(run())


def test_success_resets_failures_and_request_errors_do_not_trip() -> None:
    async def run() -> None:
        model = Model()
        breaker = CircuitBreakerChatModel(model, failure_threshold=2)
        for _ in range(3):
            model.error = ModelRequestError("bad request", provider="fake")
            with pytest.raises(ModelRequestError):
                await breaker.generate(REQUEST)
        for _ in range(3):
            model.error = ModelServerError("down", provider="fake")
            with pytest.raises(ModelServerError):
                await breaker.generate(REQUEST)
            model.error = None
            await breaker.generate(REQUEST)
        assert breaker.state is CircuitState.CLOSED

    asyncio.run(run())


@pytest.mark.parametrize("cancel_probe", [False, True])
def test_only_one_probe_and_failed_or_cancelled_probe_reopens(cancel_probe: bool) -> None:
    async def run() -> None:
        now = [0.0]
        model = Model()
        model.error = ModelServerError("down", provider="fake")
        breaker = CircuitBreakerChatModel(
            model,
            failure_threshold=1,
            recovery_seconds=10,
            clock=lambda: now[0],
        )
        with pytest.raises(ModelServerError):
            await breaker.generate(REQUEST)
        now[0] = 10
        model.entered.clear()
        model.release = asyncio.Event()
        probe = asyncio.create_task(breaker.generate(REQUEST))
        await model.entered.wait()
        with pytest.raises(CircuitOpenError):
            await breaker.generate(REQUEST)
        if cancel_probe:
            probe.cancel()
            with pytest.raises(asyncio.CancelledError):
                await probe
        else:
            model.release.set()
            with pytest.raises(ModelServerError):
                await probe
        assert breaker.state is CircuitState.OPEN
        assert model.calls == 2

    asyncio.run(run())


def test_late_success_does_not_close_newly_opened_circuit() -> None:
    async def run() -> None:
        release = asyncio.Event()
        entered = asyncio.Event()

        class ConcurrentModel(Model):
            async def generate(self, request: ChatRequest) -> ChatResult:
                self.calls += 1
                if self.calls == 1:
                    entered.set()
                    await release.wait()
                    return RESULT
                raise ModelServerError("down", provider="fake")

        breaker = CircuitBreakerChatModel(ConcurrentModel(), failure_threshold=1)
        pending = asyncio.create_task(breaker.generate(REQUEST))
        await entered.wait()
        with pytest.raises(ModelServerError):
            await breaker.generate(REQUEST)
        release.set()
        assert await pending == RESULT
        assert breaker.state is CircuitState.OPEN

    asyncio.run(run())


@pytest.mark.parametrize("seconds", [0, -1, float("nan"), float("inf")])
def test_rejects_invalid_recovery(seconds: float) -> None:
    with pytest.raises(ValueError):
        CircuitBreakerChatModel(Model(), recovery_seconds=seconds)
