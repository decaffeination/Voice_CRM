from __future__ import annotations

import json
from typing import Any

from agent.state import AgentState
from agent.tools.registry import ToolContext, registry
from main_server.core.logger import logger


def tool_node(state: AgentState) -> dict[str, Any]:
    tool_calls = state.get("tool_calls") or []
    agent_messages = list(state.get("agent_messages") or [])
    conversation_state = dict(state.get("conversation_state") or {})
    turn_count = int(conversation_state.get("turn_count") or 0)

    ctx = ToolContext(
        user_id=state.get("user_id"),
        roles=list(state.get("roles") or []),
        conversation_state=conversation_state,
        turn_count=turn_count,
        channel=state.get("channel", "text"),
    )

    accumulated: list[dict[str, Any]] = list(state.get("tool_results") or [])
    needs_confirm = bool(state.get("needs_confirm"))

    for tool_call in tool_calls:
        result = registry.execute_tool_call(tool_call, ctx)
        accumulated.append(result)
        if ctx.side_effects.get("needs_confirm"):
            needs_confirm = True

        agent_messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "content": json.dumps(result, ensure_ascii=False, default=str),
            }
        )
        logger.info(
            "agent.tool_call tool=%s summary=%s",
            (tool_call.get("function") or {}).get("name"),
            _summarize(result),
        )

    return {
        "agent_messages": agent_messages,
        "tool_calls": None,
        "conversation_state": ctx.conversation_state,
        "tool_results": accumulated,
        "tool_result": accumulated[-1] if accumulated else None,
        "needs_confirm": needs_confirm,
    }


def _summarize(result: dict[str, Any]) -> str:
    if result.get("error"):
        return f"error={result['error']}"
    if result.get("is_new"):
        return "is_new"
    if result.get("prepared"):
        return f"prepared={result.get('write_type')}"
    if result.get("sent") is not None:
        return f"sent={result.get('sent')}"
    if result.get("docs") is not None:
        if result.get("rejected"):
            return "rejected"
        return f"docs={len(result.get('docs') or [])}"
    return "ok"
