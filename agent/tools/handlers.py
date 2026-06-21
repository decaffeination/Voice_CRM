"""Tool Registry 注册与薄封装 handler（业务逻辑在 main_server.services）。"""

from __future__ import annotations

from typing import Any

import agent.tools.crm_tool as crm_tool
import agent.tools.email_tool as email_tool
import agent.tools.knowledge_tool as knowledge_tool
import agent.tools.search_tool as search_tool
import agent.tools.summary_tool as summary_tool
from agent.tools.registry import ToolContext, ToolDefinition, registry
from main_server.services.tool_result import AgentToolResult


def _apply_result(ctx: ToolContext, result: AgentToolResult) -> dict[str, Any]:
    ctx.side_effects.update(result.side_effects)
    return result.payload


def handle_crm_get_customer_profile(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    result = crm_tool.get_customer_profile_for_agent(
        conversation_state=ctx.conversation_state,
        turn_count=ctx.turn_count,
        user_id=ctx.user_id,
        roles=ctx.roles,
        customer_name=args.get("customer_name"),
        customer_id=args.get("customer_id"),
    )
    return _apply_result(ctx, result)


def handle_crm_list_employee_customers(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    return crm_tool.list_employee_customers(
        args.get("employee_name", ""),
        user_id=ctx.user_id,
        roles=ctx.roles,
    )


def handle_crm_list_recent_updates(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    days = int(args.get("days") or 30)
    result = crm_tool.list_recent_updates_for_agent(
        days=days, user_id=ctx.user_id, roles=ctx.roles
    )
    return _apply_result(ctx, result)


def handle_knowledge_search(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    return knowledge_tool.search_knowledge(args.get("query", ""))


def handle_summarize_recent_customers(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    days = int(args.get("days") or 30)
    return summary_tool.summarize_recent_customers(
        days=days, user_id=ctx.user_id, roles=ctx.roles
    )


def handle_crm_prepare_write(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    result = crm_tool.prepare_write(
        conversation_state=ctx.conversation_state,
        turn_count=ctx.turn_count,
        user_id=ctx.user_id,
        roles=ctx.roles,
        write_type=args.get("write_type") or "followup",
        action=args.get("action") or "create",
        payload=dict(args.get("payload") or {}),
        customer_name=args.get("customer_name"),
        customer_id=args.get("customer_id"),
    )
    return _apply_result(ctx, result)


def handle_email_lookup_recipient(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    result = email_tool.lookup_recipient(
        source=args.get("source") or "crm",
        conversation_state=ctx.conversation_state,
        user_id=ctx.user_id,
        turn_count=ctx.turn_count,
        customer_name=args.get("customer_name"),
        manual_email=args.get("manual_email"),
        customer_id=args.get("customer_id"),
    )
    return _apply_result(ctx, result)


def handle_email_send(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    result = email_tool.send_for_agent(
        to=args.get("to"),
        subject=args.get("subject", ""),
        body=args.get("body", ""),
        resolved_email=ctx.side_effects.get("resolved_email"),
    )
    return _apply_result(ctx, result)


def handle_web_search(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    return search_tool.web_search(
        args.get("query", ""), max_results=args.get("max_results")
    )


def _register_all() -> None:
    registry.register(
        ToolDefinition(
            name="crm_get_customer_profile",
            description="查询客户档案：联系方式、最近订单、合同、跟进。可传 customer_name；不传则使用当前会话绑定的客户。",
            parameters={
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "客户公司名称"},
                    "customer_id": {"type": "integer", "description": "客户编号"},
                },
            },
            handler=handle_crm_get_customer_profile,
        )
    )
    registry.register(
        ToolDefinition(
            name="crm_list_employee_customers",
            description="查询某职员对接的客户名单",
            parameters={
                "type": "object",
                "properties": {
                    "employee_name": {"type": "string", "description": "员工姓名"},
                },
                "required": ["employee_name"],
            },
            handler=handle_crm_list_employee_customers,
        )
    )
    registry.register(
        ToolDefinition(
            name="crm_list_recent_updates",
            description="查询最近 N 天有更新的客户列表，用于「最近一周/一月更新了哪些客户」",
            parameters={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "天数，默认30"},
                },
            },
            handler=handle_crm_list_recent_updates,
        )
    )
    registry.register(
        ToolDefinition(
            name="knowledge_search",
            description="检索公司知识库：制度、流程、报销、请假、合同模板等政策文档",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索问题"},
                },
                "required": ["query"],
            },
            handler=handle_knowledge_search,
        )
    )
    registry.register(
        ToolDefinition(
            name="summarize_recent_customers",
            description="汇总最近 N 天有合作的客户更新",
            parameters={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "天数"},
                },
            },
            handler=handle_summarize_recent_customers,
        )
    )
    registry.register(
        ToolDefinition(
            name="crm_prepare_write",
            description=(
                "准备 CRM 增/改/删（不会立即写库，需用户确认）。"
                "action: create|update|delete（默认 create）。"
                "write_type: customer|followup|contract|order。"
                "新增跟进 payload: {content, followup_type}。"
                "修改客户 payload: {customer_id, phone/email/...}。"
                "删除跟进 payload: {followup_id}。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "delete"],
                        "description": "操作类型，默认 create",
                    },
                    "write_type": {
                        "type": "string",
                        "enum": ["customer", "followup", "contract", "order"],
                    },
                    "customer_name": {"type": "string"},
                    "customer_id": {"type": "integer"},
                    "payload": {"type": "object"},
                },
                "required": ["write_type", "payload"],
            },
            handler=handle_crm_prepare_write,
        )
    )
    registry.register(
        ToolDefinition(
            name="email_lookup_recipient",
            description=(
                "解析邮件收件人。source=crm 从数据库查邮箱；"
                "source=web 联网搜索公司联系邮箱；source=manual 使用 manual_email 或提示用户口述"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "enum": ["crm", "web", "manual"]},
                    "customer_name": {"type": "string"},
                    "manual_email": {"type": "string"},
                },
                "required": ["source"],
            },
            handler=handle_email_lookup_recipient,
        )
    )
    registry.register(
        ToolDefinition(
            name="email_send",
            description="发送邮件。to 可省略若已通过 email_lookup_recipient 解析",
            parameters={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["subject", "body"],
            },
            handler=handle_email_send,
        )
    )
    registry.register(
        ToolDefinition(
            name="web_search",
            description="联网搜索公开信息，补充 CRM/知识库没有的数据",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"},
                },
                "required": ["query"],
            },
            handler=handle_web_search,
        )
    )


_register_all()
