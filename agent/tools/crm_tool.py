"""Agent CRM 工具封装 → main_server.services.crm_service。"""

from __future__ import annotations

from typing import Any

from agent.state import ConversationState
from main_server.services.crm_service import crm_service
from main_server.services.tool_result import AgentToolResult


def lookup_customer(name: str, user_id: int | None = None) -> dict[str, Any]:
    return crm_service.lookup_customer(name, user_id=user_id).model_dump()


def get_customer_profile(
    customer_id: int,
    user_id: int | None = None,
) -> dict[str, Any]:
    return crm_service.get_customer_profile(customer_id, user_id=user_id)


def get_customer_profile_by_name(
    name: str,
    user_id: int | None = None,
) -> dict[str, Any]:
    return crm_service.get_customer_profile_by_name(name, user_id=user_id)


def list_recent_updates(
    days: int = 30,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    return crm_service.list_recent_updates(days=days, user_id=user_id)


def list_employee_customers(
    employee_name: str,
    user_id: int | None = None,
    roles: list[str] | None = None,
) -> dict[str, Any]:
    return crm_service.list_employee_customers(
        employee_name, user_id=user_id, roles=roles
    )


def execute_write(
    write_type: str,
    payload: dict[str, Any],
    user_id: int | None = None,
    roles: list[str] | None = None,
    action: str = "create",
) -> dict[str, Any]:
    return crm_service.execute_write(
        write_type,
        payload,
        user_id=user_id,
        roles=roles,
        action=action,
    )


def build_pending_write(
    write_type: str,
    payload: dict[str, Any],
    turn_count: int,
) -> dict[str, Any]:
    return crm_service.build_pending_write(write_type, payload, turn_count)


def get_customer_profile_for_agent(
    *,
    conversation_state: ConversationState,
    turn_count: int,
    user_id: int | None,
    customer_name: str | None = None,
    customer_id: int | None = None,
    roles: list[str] | None = None,
) -> AgentToolResult:
    return crm_service.get_customer_profile_for_agent(
        conversation_state=conversation_state,
        turn_count=turn_count,
        user_id=user_id,
        customer_name=customer_name,
        customer_id=customer_id,
        roles=roles,
    )


def list_recent_updates_for_agent(
    *, days: int, user_id: int | None, roles: list[str] | None = None
) -> AgentToolResult:
    return crm_service.list_recent_updates_for_agent(
        days=days, user_id=user_id, roles=roles
    )


def prepare_write(
    *,
    conversation_state: ConversationState,
    turn_count: int,
    user_id: int | None,
    write_type: str,
    payload: dict[str, Any],
    customer_name: str | None = None,
    customer_id: int | None = None,
    roles: list[str] | None = None,
    action: str = "create",
) -> AgentToolResult:
    return crm_service.prepare_write(
        conversation_state=conversation_state,
        turn_count=turn_count,
        user_id=user_id,
        write_type=write_type,
        payload=payload,
        customer_name=customer_name,
        customer_id=customer_id,
        roles=roles,
        action=action,
    )


def summarize_recent_customers(
    *, days: int = 30, user_id: int | None = None, roles: list[str] | None = None
) -> dict[str, Any]:
    return crm_service.summarize_recent_customers(
        days=days, user_id=user_id, roles=roles
    )
