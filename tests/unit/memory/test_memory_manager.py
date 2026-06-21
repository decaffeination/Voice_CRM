"""MemoryManager 单元测试。"""

from __future__ import annotations

from main_server.memory.memory_manager import memory_manager


class TestMemoryManager:
    def test_save_and_load_snapshot(self, memory_db) -> None:
        # 场景：快照读写；输入：history + state + summary；预期：load 一致
        session_id = "mem-mgr-test"
        memory_manager.save_history(
            session_id,
            [{"role": "user", "content": "你好", "channel": "text"}],
        )
        memory_manager.save_state(session_id, {"turn_count": 2, "current_intent": "chat"})
        memory_manager.save_summary(session_id, "摘要内容")

        snap = memory_manager.load_snapshot(session_id, user_id=1)
        assert snap.session_id == session_id
        assert len(snap.history) >= 1
        assert snap.state.get("turn_count") == 2
        assert snap.summary == "摘要内容"

    def test_delete_session_data(self, memory_db) -> None:
        # 场景：级联删除；输入：已有数据；预期：计数 > 0 后清空
        session_id = "mem-delete-test"
        memory_manager.save_history(
            session_id,
            [{"role": "user", "content": "x", "channel": "text"}],
        )
        memory_manager.save_state(session_id, {"turn_count": 1})
        deleted = memory_manager.delete_session_data(session_id)
        assert deleted["messages"] >= 1
        assert memory_manager.load_history(session_id) == []
