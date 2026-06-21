"""LangGraph Memory 节点：会话持久化的唯一读写入口。

职责划分
--------
- **Memory（chat_message / chat_state / chat_summary）**
  业务真相源：对话历史、会话业务状态、长对话摘要。
  本模块的 ``memory_load_node`` / ``memory_save_node`` 是 Graph 内唯读写点。

- **LangGraph Checkpointer（agent/checkpoint_factory.py）**
  仅预留给人机协同 / 中断恢复等运行时能力，**不**持久化业务 Memory。
  当前 Graph 编译时不挂载 Checkpointer，避免与 Memory 双写。
"""

from __future__ import annotations

from typing import Any

from agent.state import AgentState, default_conversation_state
from main_server.core.logger import logger
from main_server.memory.memory_manager import memory_manager


def memory_load_node(state: AgentState) -> dict[str, Any]:
    """从 Memory 加载快照，组装本轮 Agent 输入。"""
    session_id = state.get("session_id", "")
    user_input = state.get("user_input", "")
    user_id = state.get("user_id")

    snapshot = memory_manager.load_snapshot(session_id, user_id=user_id)
    conversation_state = dict(snapshot.state or default_conversation_state())
    conversation_state["turn_count"] = (
        int(conversation_state.get("turn_count") or 0) + 1
    )

    messages = memory_manager.messages_from_snapshot(snapshot)
    if user_input:
        messages.append({"role": "user", "content": user_input})

    logger.info(
        "agent.memory_load session_id=%s turn_count=%s history_len=%s has_summary=%s",
        session_id,
        conversation_state["turn_count"],
        len(snapshot.history),
        bool(snapshot.summary),
    )

    return {
        "messages": messages,
        "conversation_state": conversation_state,
    }


def memory_save_node(state: AgentState) -> dict[str, Any]:
    """将本轮对话与业务状态写回 Memory。"""
    session_id = state.get("session_id", "")
    user_input = state.get("user_input", "")
    channel = state.get("channel", "text")
    final_response = state.get("final_response", "")
    conversation_state = state.get("conversation_state") or default_conversation_state()

    if not session_id:
        logger.warning("agent.memory_save skipped: missing session_id")
        return {}

    memory_manager.save_history(
        session_id,
        [
            {"role": "user", "content": user_input, "channel": channel},
            {"role": "assistant", "content": final_response, "channel": channel},
        ],
    )
    memory_manager.save_state(session_id, conversation_state)
    memory_manager.maybe_summarize(session_id)

    logger.info(
        "agent.memory_save session_id=%s turn_count=%s response_len=%s",
        session_id,
        conversation_state.get("turn_count"),
        len(final_response),
    )

    return {}
