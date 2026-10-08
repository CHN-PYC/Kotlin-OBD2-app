import asyncio
from collections.abc import Awaitable, Callable

import pytest

from app.providers.chat import ChatMessage, ChatRequest, ChatResult
from app.providers.errors import InvalidModelResponseError, ModelTimeoutError
from app.providers.retry import RetryingChatModel


class ScriptedChatModel:
    provider_name = "fake"
    model_name = "fake-chat"

    def __init__(self, outcomes: list[ChatResult | Exception]) -> None:
        self._outcomes = outcomes
        self.calls = 0

    async def generate(self, request: ChatRequest) -> ChatResult:
        outcome = self._outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _result() -> ChatResult:
    return ChatResult(
        content="grounded answer",
        provider="fake",
        model="fake-chat",
        finish_reason="stop",
        input_tokens=10,
        output_tokens=4,
    )


def _request() -> ChatRequest:
    return ChatRequest(messages=[ChatMessage(role="user", content="question")])


def _recording_sleep(delays: list[float]) -> Callable[[float], Awaitable[None]]:
    async def sleep(delay: float) -> None:
        delays.append(delay)

    return sleep


def test_retrying_model_returns_first_success_without_sleeping() -> None:
    delegate = ScriptedChatModel([_result()])
    delays: list[float] = []
    model = RetryingChatModel(
        delegate,
        max_attempts=3,
        base_delay_seconds=0.1,
        sleep=_recording_sleep(delays),
    )

    result = asyncio.run(model.generate(_request()))

    assert result.content == "grounded answer"
    assert delegate.calls == 1
    assert delays == []


def test_retrying_model_retries_transient_errors_with_exponential_backoff() -> None:
    timeout = ModelTimeoutError("slow", provider="fake", model="fake-chat")
    delegate = ScriptedChatModel([timeout, timeout, _result()])
    delays: list[float] = []
    model = RetryingChatModel(
        delegate,
        max_attempts=3,
        base_delay_seconds=0.1,
        sleep=_recording_sleep(delays),
    )

    result = asyncio.run(model.generate(_request()))

    assert result.content == "grounded answer"
    assert delegate.calls == 3
    assert delays == [0.1, 0.2]


def test_retrying_model_does_not_retry_non_retryable_model_error() -> None:
    invalid = InvalidModelResponseError("bad payload", provider="fake", model="fake-chat")
    delegate = ScriptedChatModel([invalid, _result()])
    delays: list[float] = []
    model = RetryingChatModel(
        delegate,
        max_attempts=3,
        base_delay_seconds=0.1,
        sleep=_recording_sleep(delays),
    )

    with pytest.raises(InvalidModelResponseError):
        asyncio.run(model.generate(_request()))

    assert delegate.calls == 1
    assert delays == []


def test_retrying_model_stops_after_max_attempts() -> None:
    timeout = ModelTimeoutError("slow", provider="fake", model="fake-chat")
    delegate = ScriptedChatModel([timeout, timeout, timeout])
    delays: list[float] = []
    model = RetryingChatModel(
        delegate,
        max_attempts=3,
        base_delay_seconds=0.1,
        sleep=_recording_sleep(delays),
    )

    with pytest.raises(ModelTimeoutError):
        asyncio.run(model.generate(_request()))

    assert delegate.calls == 3
    assert delays == [0.1, 0.2]


def test_retrying_model_does_not_hide_programming_error() -> None:
    delegate = ScriptedChatModel([ValueError("bug"), _result()])
    model = RetryingChatModel(delegate, max_attempts=3, base_delay_seconds=0)

    with pytest.raises(ValueError, match="bug"):
        asyncio.run(model.generate(_request()))

    assert delegate.calls == 1


@pytest.mark.parametrize(
    ("max_attempts", "base_delay_seconds"),
    [(0, 0.1), (6, 0.1), (3, -0.1)],
)
def test_retrying_model_rejects_unsafe_policy(
    max_attempts: int,
    base_delay_seconds: float,
) -> None:
    with pytest.raises(ValueError):
        RetryingChatModel(
            ScriptedChatModel([_result()]),
            max_attempts=max_attempts,
            base_delay_seconds=base_delay_seconds,
        )
