from __future__ import annotations

from typing import Any, Literal, TypedDict


class CustomerContext(TypedDict, total=False):
    customer_id: int | None
    customer_name: str | None
    is_new: bool
    bound_at_turn: int


class PendingWrite(TypedDict, total=False):
    action: str
    type: str
    payload: dict[str, Any]
    before: dict[str, Any]
    status: str
    created_at_turn: int


class ConversationState(TypedDict, total=False):
    """业务会话状态；唯一持久化于 Memory（chat_state），不经 Checkpointer 存储。"""

    customer_context: CustomerContext
    pending_write: PendingWrite | None
    current_intent: str | None
    turn_count: int


class AgentState(TypedDict, total=False):
    """LangGraph 单轮运行时状态（不持久化；持久化由 memory_node 负责）。"""

    session_id: str
    messages: list[dict[str, str]]
    user_input: str
    channel: str
    user_id: int | None
    conversation_state: ConversationState
    route: dict[str, Any]
    intent: str
    tool_result: Any
    needs_confirm: bool
    roles: list[str]
    final_response: str
    agent_messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]] | None
    tool_results: list[Any]
    step_count: int
    citations: list[dict[str, Any]]


def default_customer_context() -> CustomerContext:
    return {
        "customer_id": None,
        "customer_name": None,
        "is_new": False,
        "bound_at_turn": 0,
    }


def default_conversation_state() -> ConversationState:
    return {
        "customer_context": default_customer_context(),
        "pending_write": None,
        "current_intent": None,
        "turn_count": 0,
    }


def bind_customer(
    state: ConversationState,
    *,
    customer_id: int,
    customer_name: str,
    turn_count: int,
) -> None:
    ctx = state.setdefault("customer_context", default_customer_context())
    ctx["customer_id"] = customer_id
    ctx["customer_name"] = customer_name
    ctx["is_new"] = False
    ctx["bound_at_turn"] = turn_count


def mark_new_customer(
    state: ConversationState,
    *,
    customer_name: str,
    turn_count: int,
) -> None:
    ctx = state.setdefault("customer_context", default_customer_context())
    ctx["customer_id"] = None
    ctx["customer_name"] = customer_name
    ctx["is_new"] = True
    ctx["bound_at_turn"] = turn_count


IntentType = Literal[
    "crm_query",
    "crm_write",
    "knowledge",
    "confirm",
    "cancel",
    "chitchat",
]
