from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class ChatRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    role: ChatRole
    content: str = Field(min_length=1)


class ChatOptions(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    temperature: float = Field(default=0.0, ge=0, le=2, allow_inf_nan=False)
    max_output_tokens: int = Field(default=512, ge=1, le=8192)


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    messages: list[ChatMessage] = Field(min_length=1)
    options: ChatOptions = Field(default_factory=ChatOptions)


class ChatResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    content: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    finish_reason: str = Field(min_length=1)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


@runtime_checkable
class ChatModel(Protocol):
    # LEARNING: Protocol 类似 Java 接口；调用方依赖能力，不绑定 Ollama 实现。
    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    async def generate(self, request: ChatRequest) -> ChatResult: ...
