from __future__ import annotations

from typing import Any

from agent.state import ConversationState
from main_server.providers.Tools.email_tool import get_email_provider
from main_server.services.crm_service import crm_service
from main_server.services.tool_result import AgentToolResult
from main_server.services.search_service import search_service


class EmailService:
    """邮件相关业务：收件人解析与发送。"""

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> dict[str, Any]:
        return get_email_provider().send(
            to=to, subject=subject, body=body, html_body=html_body
        )

    def lookup_recipient(
        self,
        *,
        source: str,
        conversation_state: ConversationState,
        user_id: int | None,
        turn_count: int,
        customer_name: str | None = None,
        manual_email: str | None = None,
        customer_id: int | None = None,
    ) -> AgentToolResult:
        source = (source or "crm").lower()

        if source == "manual":
            if manual_email:
                return AgentToolResult(
                    payload={"source": "manual", "email": manual_email},
                    side_effects={"resolved_email": manual_email},
                )
            return AgentToolResult(
                payload={
                    "source": "manual",
                    "needs_input": True,
                    "message": "请用户提供收件邮箱地址",
                }
            )

        if source == "web":
            name = customer_name or self._customer_name_from_state(conversation_state)
            if not name:
                return AgentToolResult(
                    payload={"error": "validation", "message": "联网搜索需要公司名称"}
                )
            result = search_service.search_company_contact(name)
            side_effects: dict[str, Any] = {}
            emails = result.get("emails_found") or []
            if emails:
                side_effects["resolved_email"] = emails[0]
            return AgentToolResult(payload=result, side_effects=side_effects)

        return self._lookup_from_crm(
            conversation_state=conversation_state,
            user_id=user_id,
            turn_count=turn_count,
            customer_name=customer_name,
            customer_id=customer_id,
        )

    def send_for_agent(
        self,
        *,
        to: str | None,
        subject: str,
        body: str,
        resolved_email: str | None = None,
    ) -> AgentToolResult:
        recipient = to or resolved_email
        if not recipient:
            return AgentToolResult(
                payload={
                    "sent": False,
                    "needs_input": True,
                    "message": "缺少收件人邮箱，请先调用 email_lookup_recipient 或请用户提供",
                }
            )
        return AgentToolResult(payload=self.send(to=recipient, subject=subject, body=body))

    def _lookup_from_crm(
        self,
        *,
        conversation_state: ConversationState,
        user_id: int | None,
        turn_count: int,
        customer_name: str | None,
        customer_id: int | None,
    ) -> AgentToolResult:
        name = customer_name or self._customer_name_from_state(conversation_state)

        if name:
            profile_result = crm_service.get_customer_profile_by_name(
                name, user_id=user_id
            )
            if profile_result.get("profile"):
                customer = profile_result["profile"].get("customer") or profile_result.get(
                    "customer"
                )
                email = (customer or {}).get("email")
                if email:
                    return AgentToolResult(
                        payload={"source": "crm", "email": email, "customer": customer},
                        side_effects={"resolved_email": email},
                    )
            if profile_result.get("is_new"):
                return AgentToolResult(
                    payload={
                        "source": "crm",
                        "is_new": True,
                        "message": "CRM 中无该客户邮箱，可改用 web 搜索或 manual 输入",
                    }
                )

        resolved_id, err = crm_service.resolve_customer_id(
            conversation_state=conversation_state,
            turn_count=turn_count,
            user_id=user_id,
            customer_id=customer_id,
            customer_name=customer_name,
        )
        if resolved_id:
            profile = crm_service.get_customer_profile(resolved_id, user_id=user_id)
            customer = profile.get("customer") or {}
            email = customer.get("email")
            if email:
                return AgentToolResult(
                    payload={"source": "crm", "email": email, "customer": customer},
                    side_effects={"resolved_email": email},
                )

        return AgentToolResult(
            payload={
                "source": "crm",
                "needs_input": True,
                "message": "CRM 未找到邮箱，请用户口述邮箱或改用 web 搜索",
            }
        )

    @staticmethod
    def _customer_name_from_state(conversation_state: ConversationState) -> str | None:
        customer_ctx = conversation_state.get("customer_context") or {}
        return customer_ctx.get("customer_name")


email_service = EmailService()
