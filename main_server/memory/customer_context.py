"""客户上下文辅助函数，ConversationState 为唯一业务状态源。"""

from __future__ import annotations

from agent.state import (
    ConversationState,
    bind_customer,
    default_customer_context,
    mark_new_customer,
)


def clear_customer(state: ConversationState) -> None:
    state["customer_context"] = default_customer_context()


__all__ = [
    "bind_customer",
    "mark_new_customer",
    "clear_customer",
    "default_customer_context",
]
