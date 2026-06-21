from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentToolResult:
    """Agent 工具执行结果（含可选 side_effects 供 tool_node 合并）。"""

    payload: dict[str, Any]
    side_effects: dict[str, Any] = field(default_factory=dict)
