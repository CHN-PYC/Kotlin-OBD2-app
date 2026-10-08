import asyncio
from collections.abc import Sequence

import pytest
from pydantic import ValidationError

from app.providers.chat import (
    ChatMessage,
    ChatModel,
    ChatOptions,
    ChatRequest,
    ChatResult,
    ChatRole,
)


class FakeChatModel:
    provider_name = "fake"
    model_name = "fake-chat"

    async def generate(self, request: ChatRequest) -> ChatResult:
        return ChatResult(
            content=f"echo: {request.messages[-1].content}",
            provider=self.provider_name,
            model=self.model_name,
            finish_reason="stop",
            input_tokens=10,
            output_tokens=4,
        )


def test_chat_message_accepts_known_roles() -> None:
    messages: Sequence[ChatMessage] = [
        ChatMessage(role="system", content="Answer with grounded evidence."),
        ChatMessage(role="user", content="Why is coolant temperature high?"),
        ChatMessage(role="assistant", content="Check the cooling system."),
    ]

    assert [message.role for message in messages] == [
        ChatRole.SYSTEM,
        ChatRole.USER,
        ChatRole.ASSISTANT,
    ]


def test_chat_message_rejects_unknown_role() -> None:
    with pytest.raises(ValidationError):
        ChatMessage(role="developer", content="Hidden instruction")


def test_chat_message_rejects_blank_content() -> None:
    with pytest.raises(ValidationError):
        ChatMessage(role="user", content="   ")


def test_chat_request_requires_at_least_one_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(messages=[])


def test_chat_request_supplies_deterministic_defaults() -> None:
    request = ChatRequest(messages=[ChatMessage(role="user", content="Question")])

    assert request.options.temperature == 0.0
    assert request.options.max_output_tokens == 512


@pytest.mark.parametrize("temperature", [-0.1, 2.1])
def test_chat_options_reject_temperature_outside_supported_range(
    temperature: float,
) -> None:
    with pytest.raises(ValidationError):
        ChatOptions(temperature=temperature)


def test_chat_options_rejects_non_positive_output_budget() -> None:
    with pytest.raises(ValidationError):
        ChatOptions(max_output_tokens=0)


def test_chat_result_rejects_negative_token_usage() -> None:
    with pytest.raises(ValidationError):
        ChatResult(
            content="answer",
            provider="fake",
            model="fake-chat",
            finish_reason="stop",
            input_tokens=-1,
            output_tokens=4,
        )


def test_fake_chat_model_satisfies_protocol_and_returns_typed_result() -> None:
    model = FakeChatModel()
    request = ChatRequest(messages=[ChatMessage(role="user", content="coolant question")])

    result = asyncio.run(model.generate(request))

    assert isinstance(model, ChatModel)
    assert result.content == "echo: coolant question"
    assert result.provider == "fake"
