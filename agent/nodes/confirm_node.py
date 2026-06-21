from __future__ import annotations

from typing import Any

from main_server.services.crm_service import crm_service
from agent.state import AgentState
from main_server.config.constants import (
    ENTITY_ID_KEYS,
    MUTATION_CREATE,
    MUTATION_DELETE,
    MUTATION_UPDATE,
    PENDING_WRITE_AWAITING,
    PENDING_WRITE_CONFIRMED,
    PENDING_WRITE_DRAFT,
    WRITE_TYPE_CONTRACT,
    WRITE_TYPE_CUSTOMER,
    WRITE_TYPE_FOLLOWUP,
    WRITE_TYPE_ORDER,
)
from main_server.core.exceptions import AppError


_ACTION_LABELS = {
    MUTATION_CREATE: "新增",
    MUTATION_UPDATE: "修改",
    MUTATION_DELETE: "删除",
}

_ENTITY_LABELS = {
    WRITE_TYPE_FOLLOWUP: "跟进记录",
    WRITE_TYPE_CUSTOMER: "客户",
    WRITE_TYPE_CONTRACT: "合同",
    WRITE_TYPE_ORDER: "订单",
}


def format_write_preview(pending: dict[str, Any]) -> str:
    action = pending.get("action", MUTATION_CREATE)
    write_type = pending.get("type", "")
    payload = pending.get("payload") or {}
    before = pending.get("before") or {}

    action_label = _ACTION_LABELS.get(action, action)
    entity_label = _ENTITY_LABELS.get(write_type, write_type)
    lines = [f"【{action_label}{entity_label}】"]

    if before:
        lines.append("变更前：")
        for key, value in before.items():
            lines.append(f"  - {key}: {value}")

    if action == MUTATION_DELETE:
        id_key = ENTITY_ID_KEYS.get(write_type, "id")
        lines.append(f"将删除记录 {id_key}={payload.get(id_key)}")
    else:
        lines.append("变更内容：" if action == MUTATION_UPDATE else "内容：")
        for key, value in payload.items():
            lines.append(f"  - {key}: {value}")

    return "\n".join(lines)


def confirm_node(state: AgentState) -> dict[str, Any]:
    conversation_state = dict(state.get("conversation_state") or {})
    intent = state.get("intent", "")
    pending = conversation_state.get("pending_write")
    tool_result = state.get("tool_result")
    user_id = state.get("user_id")

    if intent == "cancel":
        if pending:
            conversation_state["pending_write"] = None
        return {
            "conversation_state": conversation_state,
            "tool_result": {
                "cancelled": True,
                "previous_pending": pending,
            },
            "needs_confirm": False,
        }

    if intent == "confirm":
        if not pending:
            return {
                "conversation_state": conversation_state,
                "tool_result": {"error": "no_pending", "message": "没有待确认操作"},
                "needs_confirm": False,
            }
        if pending.get("status") != PENDING_WRITE_AWAITING:
            return {
                "conversation_state": conversation_state,
                "tool_result": {
                    "error": "invalid_pending_status",
                    "status": pending.get("status"),
                },
                "needs_confirm": False,
            }
        write_type = pending["type"]
        action = pending.get("action", MUTATION_CREATE)
        payload = dict(pending["payload"])
        try:
            result = crm_service.execute_write(
                write_type,
                payload,
                user_id=user_id,
                roles=list(state.get("roles") or []),
                action=action,
            )
        except AppError as exc:
            return {
                "conversation_state": conversation_state,
                "tool_result": {"error": "write_failed", "message": str(exc)},
                "needs_confirm": False,
            }
        conversation_state["pending_write"] = None
        return {
            "conversation_state": conversation_state,
            "tool_result": {
                "mutated": True,
                "written": action == MUTATION_CREATE,
                "updated": action == MUTATION_UPDATE,
                "deleted": action == MUTATION_DELETE,
                "action": action,
                "write_type": write_type,
                "status": PENDING_WRITE_CONFIRMED,
                "result": result,
            },
            "needs_confirm": False,
        }

    if pending and pending.get("status") == PENDING_WRITE_DRAFT:
        pending = dict(pending)
        pending["status"] = PENDING_WRITE_AWAITING
        conversation_state["pending_write"] = pending
        return {
            "conversation_state": conversation_state,
            "tool_result": {
                "awaiting_confirm": True,
                "pending_write": pending,
                "preview_text": format_write_preview(pending),
                "preview": tool_result,
            },
            "needs_confirm": False,
        }

    return {
        "conversation_state": conversation_state,
        "needs_confirm": False,
    }
