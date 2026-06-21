"""会话管理单元测试。"""

from __future__ import annotations

import pytest

from main_server.core.exceptions import NotFoundError, PermissionDeniedError
from main_server.session.session_manager import session_manager


class TestSessionManager:
    def test_create_and_get(self, memory_db) -> None:
        # 场景：创建并获取会话；输入：user_id=1；预期：session_id 一致
        session = session_manager.create(1, title="测试会话")
        fetched = session_manager.get(session.session_id, 1)
        assert fetched.session_id == session.session_id
        assert fetched.title == "测试会话"

    def test_list_by_user(self, memory_db) -> None:
        # 场景：用户会话列表；输入：创建 2 个会话；预期：total>=2
        session_manager.create(1, title="A")
        session_manager.create(1, title="B")
        sessions = session_manager.list_by_user(1)
        assert len(sessions) >= 2

    def test_get_other_user_forbidden(self, memory_db) -> None:
        # 场景：越权访问会话；输入：user2 访问 user1 会话；预期：403
        session = session_manager.create(1, title="私有")
        with pytest.raises(PermissionDeniedError, match="无权"):
            session_manager.get(session.session_id, 999)

    def test_get_not_found(self, memory_db) -> None:
        # 场景：会话不存在；输入：随机 session_id；预期：404
        with pytest.raises(NotFoundError, match="不存在"):
            session_manager.get("non-existent-id", 1)

    def test_ensure_session_creates_new(self, memory_db) -> None:
        # 场景：无 session_id 时创建；输入：None；预期：返回新 id
        sid = session_manager.ensure_session(None, 1)
        assert sid
        assert session_manager.get(sid, 1)

    def test_ensure_session_reuses_existing(self, memory_db) -> None:
        # 场景：已有 session_id；输入：有效 id；预期：复用同一 id
        created = session_manager.create(1)
        sid = session_manager.ensure_session(created.session_id, 1)
        assert sid == created.session_id

    def test_delete_session(self, memory_db) -> None:
        # 场景：删除会话；输入：有效 session；预期：再次 get 404
        session = session_manager.create(1)
        memory_deleted = session_manager.delete(session.session_id, 1)
        assert isinstance(memory_deleted, dict)
        with pytest.raises(NotFoundError):
            session_manager.get(session.session_id, 1)

    def test_touch_updates_last_active(self, memory_db) -> None:
        # 场景：touch 更新活跃时间；输入：创建后 touch；预期：不抛异常
        session = session_manager.create(1)
        touched = session_manager.touch(session.session_id, 1)
        assert touched.session_id == session.session_id

    def test_maybe_auto_title_on_first_message(self, memory_db) -> None:
        # 场景：首条消息自动标题；输入：默认标题会话；预期：标题更新
        session = session_manager.create(1)
        updated = session_manager.maybe_auto_title(
            session.session_id, 1, "查询客户联系方式"
        )
        assert updated is not None
        assert updated.title == "查询客户联系方式"
        info = session_manager.get(session.session_id, 1)
        assert info.title == "查询客户联系方式"

    def test_maybe_auto_title_skips_renamed(self, memory_db) -> None:
        # 场景：已自定义标题；输入：第二条消息；预期：不覆盖
        session = session_manager.create(1, title="我的会话")
        updated = session_manager.maybe_auto_title(
            session.session_id, 1, "另一条消息"
        )
        assert updated is None
        info = session_manager.get(session.session_id, 1)
        assert info.title == "我的会话"

    def test_derive_session_title_truncates(self) -> None:
        from main_server.session.session_manager import derive_session_title

        long_text = "这是一段非常非常非常非常非常非常非常非常长的用户消息"
        title = derive_session_title(long_text, max_len=10)
        assert title.endswith("…")
        assert len(title) == 10
