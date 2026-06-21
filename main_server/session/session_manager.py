from __future__ import annotations

import uuid

import main_server.session.session_store as session_store
from main_server.core.exceptions import NotFoundError, PermissionDeniedError
from main_server.core.logger import logger
from main_server.session.session_schema import SessionInfo

DEFAULT_SESSION_TITLE = "新会话"
SESSION_TITLE_MAX_LEN = 32


def derive_session_title(
    message: str, max_len: int = SESSION_TITLE_MAX_LEN
) -> str:
    """从用户首条消息截取会话标题。"""
    normalized = " ".join(message.strip().split())
    if not normalized:
        return DEFAULT_SESSION_TITLE
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 1] + "…"


class SessionManager:
    """会话生命周期管理，唯一读写 session_store 的入口。"""

    def create(self, user_id: int, title: str = DEFAULT_SESSION_TITLE) -> SessionInfo:
        session_id = str(uuid.uuid4())
        info = session_store.create(session_id, user_id, title)
        logger.info("session.create session_id=%s title=%s", session_id, title)
        return info

    def get(self, session_id: str, user_id: int) -> SessionInfo:
        info = session_store.get(session_id)
        if info is None:
            raise NotFoundError("会话不存在")
        if info.user_id != user_id:
            raise PermissionDeniedError("无权访问该会话")
        logger.info("session.get session_id=%s", session_id)
        return info

    def list_by_user(self, user_id: int) -> list[SessionInfo]:
        return session_store.list_by_user(user_id)

    def touch(self, session_id: str, user_id: int) -> SessionInfo:
        info = self.get(session_id, user_id)
        updated = session_store.touch(session_id)
        logger.info("session.touch session_id=%s", session_id)
        return updated or info

    def ensure_session(
        self,
        session_id: str | None,
        user_id: int,
        title: str = DEFAULT_SESSION_TITLE,
    ) -> str:
        """获取已有会话或创建新会话，返回 session_id。"""
        if session_id:
            self.touch(session_id, user_id)
            return session_id
        return self.create(user_id, title).session_id

    def delete(self, session_id: str, user_id: int) -> dict[str, int]:
        """删除会话元数据并级联清理 Memory。"""
        from main_server.memory.memory_manager import memory_manager

        self.get(session_id, user_id)
        memory_deleted = memory_manager.delete_session_data(session_id)
        if not session_store.delete(session_id):
            raise NotFoundError("会话不存在")
        logger.info("session.delete session_id=%s user_id=%s", session_id, user_id)
        return memory_deleted

    def maybe_auto_title(
        self, session_id: str, user_id: int, message: str
    ) -> SessionInfo | None:
        """首条消息后将默认标题「新会话」替换为用户消息摘要。"""
        info = self.get(session_id, user_id)
        if info.title != DEFAULT_SESSION_TITLE:
            return None
        title = derive_session_title(message)
        if title == DEFAULT_SESSION_TITLE:
            return None
        updated = session_store.update_title(session_id, title)
        if updated is None:
            return None
        logger.info("session.auto_title session_id=%s title=%s", session_id, title)
        return updated


session_manager = SessionManager()
