"""Agent 汇总工具封装 → main_server.services.crm_service。"""

from __future__ import annotations

from typing import Any

import agent.tools.crm_tool as crm_tool


def summarize_recent_customers(
    days: int = 30,
    user_id: int | None = None,
    roles: list[str] | None = None,
) -> dict[str, Any]:
    return crm_tool.summarize_recent_customers(
        days=days, user_id=user_id, roles=roles
    )
