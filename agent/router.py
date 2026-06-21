"""Function Calling Graph 路由：pending 拦截 + 条件边。

主流程:
  memory_load → pending_gate → agent ⇄ tools → confirm? → response → memory_save

- pending_gate: 有待确认写入时，关键词「确认/取消」直接走 confirm，不经过 LLM
- route_after_agent: 有 tool_calls → tools；有 draft pending → confirm；否则 → response
- route_after_tools: 未超 max_steps → 继续 agent；否则 → response
"""

from __future__ import annotations

from typing import Any, Literal

from agent.state import AgentState
from main_server.config.constants import PENDING_WRITE_AWAITING, PENDING_WRITE_DRAFT
from main_server.core.logger import logger


def _keyword_confirm(text: str) -> bool:
    keys = ("确认", "确定", "是的", "好的", "写入", "可以", "同意")
    return any(k in text for k in keys)


def _keyword_cancel(text: str) -> bool:
    keys = ("取消", "不要", "算了", "不写了", "放弃")
    return any(k in text for k in keys)


def pending_gate_node(state: AgentState) -> dict[str, Any]:
    """入口路由：拦截待确认写入的确认/取消，其余进入 FC Agent。"""
    user_input = state.get("user_input", "")
    conversation_state = dict(state.get("conversation_state") or {})
    pending = conversation_state.get("pending_write")

    if pending and pending.get("status") == PENDING_WRITE_AWAITING:
        if _keyword_confirm(user_input):
            logger.info("agent.route pending_gate intent=confirm")
            return {"intent": "confirm"}
        if _keyword_cancel(user_input):
            logger.info("agent.route pending_gate intent=cancel")
            return {"intent": "cancel"}
        logger.info("agent.route pending_gate intent=pending_reminder")
        return {
            "intent": "pending_reminder",
            "tool_result": {"pending_reminder": True},
        }

    logger.info("agent.route pending_gate intent=agent")
    return {"intent": "agent"}


def route_after_pending_gate(
    state: AgentState,
) -> Literal["confirm", "response", "agent"]:
    intent = state.get("intent", "agent")
    if intent in ("confirm", "cancel"):
        return "confirm"
    if intent == "pending_reminder":
        return "response"
    return "agent"


def route_after_agent(
    state: AgentState,
) -> Literal["tools", "confirm", "response"]:
    if state.get("tool_calls"):
        logger.info(
            "agent.route after_agent next=tools count=%s",
            len(state.get("tool_calls") or []),
        )
        return "tools"
    pending = (state.get("conversation_state") or {}).get("pending_write")
    if pending and pending.get("status") == PENDING_WRITE_DRAFT:
        logger.info("agent.route after_agent next=confirm")
        return "confirm"
    logger.info("agent.route after_agent next=response")
    return "response"


def route_after_tools(state: AgentState) -> Literal["agent", "response"]:
    from main_server.config.settings import get_settings

    max_steps = get_settings().tools.agent.max_steps
    step_count = int(state.get("step_count") or 0)
    if step_count >= max_steps:
        logger.info(
            "agent.route after_tools next=response step_count=%s max=%s",
            step_count,
            max_steps,
        )
        return "response"
    logger.info("agent.route after_tools next=agent step_count=%s", step_count)
    return "agent"
