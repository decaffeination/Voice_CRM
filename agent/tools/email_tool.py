"""Agent 邮件工具封装 → main_server.services.email_service。"""

from __future__ import annotations

from typing import Any

from agent.state import ConversationState
from main_server.services.tool_result import AgentToolResult
from main_server.services.email_service import email_service


def send_email(
    *,
    to: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> dict[str, Any]:
    return email_service.send(to=to, subject=subject, body=body, html_body=html_body)


def lookup_recipient(
    *,
    source: str,
    conversation_state: ConversationState,
    user_id: int | None,
    turn_count: int,
    customer_name: str | None = None,
    manual_email: str | None = None,
    customer_id: int | None = None,
) -> AgentToolResult:
    return email_service.lookup_recipient(
        source=source,
        conversation_state=conversation_state,
        user_id=user_id,
        turn_count=turn_count,
        customer_name=customer_name,
        manual_email=manual_email,
        customer_id=customer_id,
    )


def send_for_agent(
    *,
    to: str | None,
    subject: str,
    body: str,
    resolved_email: str | None = None,
) -> AgentToolResult:
    return email_service.send_for_agent(
        to=to,
        subject=subject,
        body=body,
        resolved_email=resolved_email,
    )
