from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import main_server.memory.history_memory as history_memory
import main_server.memory.state_memory as state_memory
import main_server.memory.summary_memory as summary_memory
from agent.state import ConversationState, default_conversation_state
from main_server.config.settings import get_settings
from main_server.core.exceptions import AppError, MemoryError
from main_server.core.logger import logger
from main_server.memory.memory_schema import HistoryMessage, MemorySnapshot
from main_server.services.llm_service import llm_service

_T = TypeVar("_T")


def _guard_memory(operation: str, fn: Callable[[], _T]) -> _T:
    try:
        return fn()
    except AppError:
        raise
    except Exception as exc:
        raise MemoryError(f"{operation}失败") from exc


class MemoryManager:
    """Memory 统一入口：History / State / Summary 分开读写。

    Graph 内仅通过 ``agent.nodes.memory_node`` 读写；Pipeline 不再直接调用
    save_history / save_state。``load_snapshot`` 等仍可供管理/调试使用。
    """

    def load_history(self, session_id: str) -> list[HistoryMessage]:
        return _guard_memory(
            "加载对话历史",
            lambda: history_memory.load_active(session_id),
        )

    def load_history_all(self, session_id: str) -> list[HistoryMessage]:
        """加载会话全部历史（供前端展示，不受活跃轮次限制）。"""
        return _guard_memory(
            "加载完整对话历史",
            lambda: history_memory.load_all(session_id),
        )

    def load_state(self, session_id: str) -> ConversationState:
        return _guard_memory(
            "加载会话状态",
            lambda: state_memory.load(session_id),
        )

    def load_summary(self, session_id: str) -> str | None:
        return _guard_memory(
            "加载对话摘要",
            lambda: summary_memory.load(session_id),
        )

    def load_snapshot(
        self, session_id: str, *, user_id: int | None = None
    ) -> MemorySnapshot:
        return _guard_memory(
            "加载会话快照",
            lambda: MemorySnapshot(
                session_id=session_id,
                user_id=user_id,
                history=self.load_history(session_id),
                state=self.load_state(session_id),
                summary=self.load_summary(session_id),
            ),
        )

    def save_history(self, session_id: str, messages: list[dict]) -> None:
        _guard_memory(
            "保存对话历史",
            lambda: history_memory.append(session_id, messages),
        )

    def save_state(self, session_id: str, state: ConversationState) -> None:
        _guard_memory(
            "保存会话状态",
            lambda: state_memory.save(session_id, state),
        )

    def save_summary(self, session_id: str, summary: str) -> None:
        _guard_memory(
            "保存对话摘要",
            lambda: summary_memory.save(session_id, summary),
        )

    def messages_from_snapshot(
        self, snapshot: MemorySnapshot
    ) -> list[dict[str, str]]:
        """从快照组装 Agent 输入：摘要 + 最近活跃历史。"""
        messages: list[dict[str, str]] = []
        if snapshot.summary:
            messages.append(
                {
                    "role": "system",
                    "content": f"历史对话摘要：\n{snapshot.summary}",
                }
            )
        for item in snapshot.history:
            messages.append({"role": item.role, "content": item.content})
        return messages

    def history_for_agent(self, session_id: str) -> list[dict[str, str]]:
        """组装 Agent 输入：摘要 + 最近活跃历史。"""
        return self.messages_from_snapshot(self.load_snapshot(session_id))

    def maybe_summarize(self, session_id: str) -> None:
        def _run() -> None:
            settings = get_settings()
            total = history_memory.count(session_id)
            if total <= settings.memory.summary_trigger_count:
                return

            keep_last = settings.memory.history_active_rounds * 2
            old_messages = history_memory.load_older_than(session_id, keep_last)
            if not old_messages:
                return

            dialog = "\n".join(
                f"{m.role}: {m.content}" for m in old_messages
            )
            existing = self.load_summary(session_id) or ""
            prompt = (
                "请将以下对话压缩为简洁中文摘要，保留客户名、意图、关键结论。"
                "若已有摘要，请合并更新。\n\n"
                f"已有摘要:\n{existing}\n\n"
                f"待压缩对话:\n{dialog}"
            )
            new_summary = llm_service.summarize_dialog(prompt).strip()
            self.save_summary(session_id, new_summary)
            deleted = history_memory.delete_older_than(session_id, keep_last)
            logger.info(
                "会话 %s 摘要已更新，清理历史消息 %s 条",
                session_id,
                deleted,
            )

        _guard_memory("生成对话摘要", _run)

    def delete_session_data(self, session_id: str) -> dict[str, int]:
        """删除会话全部 Memory 数据（history / state / summary）。"""

        def _run() -> dict[str, int]:
            deleted_messages = history_memory.delete_all(session_id)
            deleted_state = state_memory.delete(session_id)
            deleted_summary = summary_memory.delete(session_id)
            logger.info(
                "memory.delete_session session_id=%s messages=%s state=%s summary=%s",
                session_id,
                deleted_messages,
                deleted_state,
                deleted_summary,
            )
            return {
                "messages": deleted_messages,
                "state": deleted_state,
                "summary": deleted_summary,
            }

        return _guard_memory("删除会话记忆", _run)


memory_manager = MemoryManager()
