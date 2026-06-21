from __future__ import annotations

import json
from typing import Any

from agent.state import AgentState
from agent.tools.registry import registry
from main_server.config.prompt import TOOL_AGENT_SYSTEM
from main_server.core.logger import logger
from main_server.services.llm_service import llm_service


def _build_agent_messages(state: AgentState) -> list[dict[str, Any]]:
    existing = state.get("agent_messages")
    if existing:
        return list(existing)

    messages: list[dict[str, Any]] = [{"role": "system", "content": TOOL_AGENT_SYSTEM}]
    history = state.get("messages") or []
    for item in history:
        if item.get("role") in ("user", "assistant", "system"):
            messages.append(
                {"role": item["role"], "content": item.get("content", "")}
            )

    conversation_state = state.get("conversation_state") or {}
    customer_ctx = conversation_state.get("customer_context") or {}
    pending = conversation_state.get("pending_write")
    context_note = (
        f"当前客户上下文: {json.dumps(customer_ctx, ensure_ascii=False)}\n"
        f"待确认写入: {json.dumps(pending, ensure_ascii=False)}"
    )
    user_input = state.get("user_input", "")
    messages.append(
        {
            "role": "user",
            "content": f"{context_note}\n\n用户本轮输入: {user_input}",
        }
    )
    return messages


def agent_node(state: AgentState) -> dict[str, Any]:
    agent_messages = _build_agent_messages(state)
    tools = registry.openai_schemas()

    message = llm_service.chat_with_tools(agent_messages, tools)
    agent_messages.append(message)

    tool_calls = message.get("tool_calls")
    step_count = int(state.get("step_count") or 0) + 1
    content = message.get("content") or ""

    logger.info(
        "agent.step step=%s tool_calls=%s content_len=%s",
        step_count,
        len(tool_calls or []),
        len(content),
    )

    updates: dict[str, Any] = {
        "agent_messages": agent_messages,
        "step_count": step_count,
        "tool_calls": tool_calls,
    }

    if not tool_calls and content:
        updates["final_response"] = content
        updates["tool_result"] = {
            "agent_summary": content,
            "tool_results": state.get("tool_results") or [],
        }

    return updates
