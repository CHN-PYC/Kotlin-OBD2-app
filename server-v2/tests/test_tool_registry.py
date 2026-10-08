import asyncio
from typing import Any

import pytest
from pydantic import BaseModel

from app.tools.registry import (
    AgentTool,
    DuplicateToolError,
    ToolInputValidationError,
    ToolRegistry,
    UnknownToolError,
)


class EchoInput(BaseModel):
    value: int


class EchoOutput(BaseModel):
    value: int


class EchoTool(AgentTool):
    name = "echo"
    description = "Return a validated value."
    input_model = EchoInput
    output_model = EchoOutput

    async def execute(self, tool_input: BaseModel) -> dict[str, Any]:
        request = EchoInput.model_validate(tool_input)
        return {"value": request.value}


def test_registry_validates_and_invokes_whitelisted_tool() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    result = asyncio.run(registry.invoke("echo", {"value": 7}))

    assert result == EchoOutput(value=7)
    assert registry.names() == ["echo"]
    assert registry.definitions()[0]["function"]["parameters"]["required"] == ["value"]


def test_registry_rejects_bad_arguments_unknown_and_duplicate_tools() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    with pytest.raises(ToolInputValidationError):
        asyncio.run(registry.invoke("echo", {"value": "seven"}))
    with pytest.raises(UnknownToolError):
        asyncio.run(registry.invoke("missing", {}))
    with pytest.raises(DuplicateToolError):
        registry.register(EchoTool())
