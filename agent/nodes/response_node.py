from __future__ import annotations

import json
import re
from typing import Any

from agent.nodes.confirm_node import format_write_preview
from agent.state import AgentState
from main_server.config.prompt import RESPONSE_SYSTEM
from main_server.core.logger import logger
from main_server.core.stream_context import get_stream_emitter
from main_server.services.llm_service import llm_service

_CITATION_RETRY_HINT = (
    "你上一版回答未标注知识库引用编号。请用中文重新回答，"
    "并在相关陈述句末标注 [1]、[2] 等编号（与 citations.ref 一致）。"
)


def _template_response(state: AgentState) -> str | None:
    tool_result: dict[str, Any] = state.get("tool_result") or {}
    tool_results: list[Any] = state.get("tool_results") or []
    conversation_state = state.get("conversation_state") or {}
    pending = conversation_state.get("pending_write")

    if tool_result.get("pending_reminder") or state.get("intent") == "pending_reminder":
        preview = ""
        if pending:
            preview = f"\n待确认内容：\n{format_write_preview(pending)}"
        return (
            "您有一笔待确认写入尚未处理，请先回复「确认」执行写入，"
            f"或回复「取消」放弃。{preview}"
        )

    if tool_result.get("error") == "pending_exists":
        return "当前已有待确认写入，请先回复「确认」或「取消」后再提交新的写入。"

    if tool_result.get("awaiting_confirm"):
        preview = tool_result.get("preview_text") or format_write_preview(
            tool_result.get("pending_write") or {}
        )
        return (
            "即将变更以下内容，请回复「确认」执行，或回复「取消」放弃：\n"
            f"{preview}"
        )

    if tool_result.get("cancelled"):
        return "好的，已取消本次写入操作。"

    if tool_result.get("written"):
        result = tool_result.get("result") or {}
        write_type = tool_result.get("write_type", "记录")
        record_id = result.get("id", "未知")
        return f"已成功写入{write_type}，记录编号：{record_id}。"

    if tool_result.get("updated"):
        result = tool_result.get("result") or {}
        write_type = tool_result.get("write_type", "记录")
        record_id = result.get("id", "未知")
        return f"已成功更新{write_type}，记录编号：{record_id}。"

    if tool_result.get("deleted"):
        result = tool_result.get("result") or {}
        write_type = tool_result.get("write_type", "记录")
        record_id = result.get("id", "未知")
        if write_type == "customer":
            return f"已成功归档客户，记录编号：{record_id}。"
        return f"已成功删除{write_type}，记录编号：{record_id}。"

    if tool_result.get("error") == "no_pending":
        return "当前没有待确认写入。如需新增记录，请直接说明。"

    if tool_result.get("error") == "write_failed":
        return f"写入失败：{tool_result.get('message', '未知错误')}"

    for item in reversed(tool_results):
        if isinstance(item, dict) and item.get("is_new"):
            name = item.get("customer_name", "")
            return f"{name} 是新客户，暂无合作记录。如需新增客户，请说明客户信息。"

    for item in reversed(tool_results):
        if isinstance(item, dict) and item.get("sent"):
            to = item.get("to", "")
            dry = "（测试模式，未实际发送）" if item.get("dry_run") else ""
            return f"邮件已发送至 {to}{dry}。"

    for item in reversed(tool_results):
        if isinstance(item, dict) and item.get("needs_input"):
            return item.get("message", "请补充必要信息后继续。")

    for item in reversed(tool_results):
        if isinstance(item, dict) and (
            item.get("rejected") or item.get("error") == "no_results"
        ):
            return item.get(
                "message",
                "知识库中未找到与您问题相关的内容，请换一种问法或联系管理员。",
            )

    return None


def _collect_knowledge_citations(tool_results: list[Any]) -> list[dict[str, Any]]:
    for item in reversed(tool_results):
        if not isinstance(item, dict):
            continue
        if item.get("tool") != "knowledge_search":
            continue
        if item.get("rejected"):
            return []
        citations = item.get("citations") or []
        if citations:
            return citations
    return []


def _has_required_citations(text: str, citations: list[dict[str, Any]]) -> bool:
    if not citations:
        return True
    for citation in citations:
        ref = citation.get("ref") or f"[{citation.get('index')}]"
        if ref not in text and not re.search(
            rf"\[{citation.get('index')}\]", text
        ):
            return False
    return True


def _append_citation_footer(text: str, citations: list[dict[str, Any]]) -> str:
    lines = [text.rstrip(), "", "参考来源："]
    for citation in citations:
        page = f" 页{citation['page']}" if citation.get("page") else ""
        lines.append(f"{citation.get('ref', '')} {citation.get('source', '')}{page}")
    return "\n".join(lines)


def _enforce_citations(
    text: str,
    citations: list[dict[str, Any]],
    messages: list[dict[str, str]],
) -> str:
    if not citations or _has_required_citations(text, citations):
        return text

    logger.info("response.citation_retry missing_refs=%s", len(citations))
    retry_messages = [
        *messages,
        {"role": "assistant", "content": text},
        {"role": "user", "content": _CITATION_RETRY_HINT},
    ]
    retried = llm_service.chat(retry_messages)
    if _has_required_citations(retried, citations):
        return retried

    logger.info("response.citation_footer fallback")
    return _append_citation_footer(text, citations)


def _emit_text_final(text: str, state: AgentState) -> None:
    emitter = get_stream_emitter()
    if emitter is not None:
        intent = state.get("intent") or (
            (state.get("conversation_state") or {}).get("current_intent")
        )
        emitter.on_text_final(text, intent=intent)


def response_node(state: AgentState) -> dict[str, Any]:
    if state.get("final_response"):
        text = state["final_response"]
        _emit_text_final(text, state)
        return {"final_response": text}

    templated = _template_response(state)
    if templated is not None:
        _emit_text_final(templated, state)
        return {"final_response": templated}

    user_input = state.get("user_input", "")
    tool_results = state.get("tool_results") or []
    tool_result = state.get("tool_result")
    conversation_state = state.get("conversation_state") or {}
    customer_ctx = conversation_state.get("customer_context") or {}

    payload = tool_results if tool_results else ([tool_result] if tool_result else [])
    citations = _collect_knowledge_citations(
        tool_results if tool_results else ([tool_result] if tool_result else [])
    )

    messages = [
        {"role": "system", "content": RESPONSE_SYSTEM},
        {
            "role": "user",
            "content": (
                f"用户说: {user_input}\n"
                f"当前客户上下文: {json.dumps(customer_ctx, ensure_ascii=False)}\n"
                f"工具结果: {json.dumps(payload, ensure_ascii=False, default=str)}"
            ),
        },
    ]

    emitter = get_stream_emitter()
    if emitter is not None:
        parts: list[str] = []
        for delta in llm_service.chat_stream(messages):
            parts.append(delta)
            emitter.on_text_delta(delta)
        final_response = "".join(parts)
    else:
        final_response = llm_service.chat(messages)

    if citations:
        final_response = _enforce_citations(final_response, citations, messages)

    _emit_text_final(final_response, state)
    return {"final_response": final_response}
