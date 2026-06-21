from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from agent.state import ConversationState


@dataclass
class ToolContext:
    user_id: int | None
    roles: list[str]
    conversation_state: ConversationState
    turn_count: int
    channel: str = "text"
    side_effects: dict[str, Any] = field(default_factory=dict)


ToolHandler = Callable[[dict[str, Any], ToolContext], dict[str, Any]]


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def openai_schemas(self) -> list[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": "unknown_tool", "tool": name}
        try:
            return tool.handler(arguments, ctx)
        except Exception as exc:
            return {"error": "tool_failed", "tool": name, "message": str(exc)}

    def execute_tool_call(
        self, tool_call: dict[str, Any], ctx: ToolContext
    ) -> dict[str, Any]:
        fn = tool_call.get("function") or {}
        name = fn.get("name", "")
        raw_args = fn.get("arguments") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
        except json.JSONDecodeError:
            args = {}
        result = self.execute(name, args, ctx)
        result.setdefault("tool", name)
        return result


registry = ToolRegistry()
