import asyncio
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError


class ToolRegistryError(RuntimeError):
    pass


class UnknownToolError(ToolRegistryError):
    pass


class DuplicateToolError(ToolRegistryError):
    pass


class ToolTimeoutError(ToolRegistryError):
    pass


class ToolInputValidationError(ToolRegistryError):
    pass


class ToolOutputValidationError(ToolRegistryError):
    pass


class AgentTool(ABC):
    """One schema-validated capability; subclasses implement only business work."""

    name: ClassVar[str]
    description: ClassVar[str]
    input_model: ClassVar[type[BaseModel]]
    output_model: ClassVar[type[BaseModel]]
    timeout_seconds: ClassVar[float] = 30.0

    async def invoke(self, payload: dict[str, Any] | BaseModel) -> BaseModel:
        try:
            validated_input = self.input_model.model_validate(payload)
        except ValidationError as exc:
            raise ToolInputValidationError(f"invalid arguments for tool: {self.name}") from exc
        try:
            raw_output = await asyncio.wait_for(
                self.execute(validated_input),
                timeout=self.timeout_seconds,
            )
        except TimeoutError as exc:
            raise ToolTimeoutError(f"tool timed out: {self.name}") from exc
        try:
            return self.output_model.model_validate(raw_output)
        except ValidationError as exc:
            raise ToolOutputValidationError(f"invalid output from tool: {self.name}") from exc

    @abstractmethod
    async def execute(self, tool_input: BaseModel) -> BaseModel | dict[str, Any]: ...

    @classmethod
    def definition(cls) -> dict[str, Any]:
        """OpenAI-compatible function definition, without exposing the handler."""
        return {
            "type": "function",
            "function": {
                "name": cls.name,
                "description": cls.description,
                "parameters": cls.input_model.model_json_schema(),
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        if tool.name in self._tools:
            raise DuplicateToolError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    async def invoke(self, name: str, payload: dict[str, Any] | BaseModel) -> BaseModel:
        tool = self._tools.get(name)
        if tool is None:
            raise UnknownToolError(f"unknown tool: {name}")
        return await tool.invoke(payload)

    def definitions(self) -> list[dict[str, Any]]:
        return [self._tools[name].definition() for name in sorted(self._tools)]

    def names(self) -> list[str]:
        return sorted(self._tools)
