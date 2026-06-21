"""多轮 Memory 集成测试（对应 manual P6）。"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from main_server.api.chat import router as chat_router
from main_server.core.auth.permission import Role
from main_server.memory.memory_manager import memory_manager
from main_server.services.pipeline.chat_pipeline import ChatPipelineResult
from tests.conftest import auth_headers, make_test_app, token_for_user

_CHAT_PIPELINE_PATCH = "main_server.api.chat.chat_pipeline.run_async"


class TestMemoryMultiturn:
    def test_two_turns_persist_history(self, memory_db) -> None:
        # 场景：两轮对话历史持久化；输入：同 session 两轮 chat；预期：history >= 4 条
        from main_server.core.auth.user_service import create_user
        from main_server.DB import db_session

        with db_session() as session:
            user = create_user(
                session,
                username="mem_user",
                password="mem12345",
                roles=[Role.SALES],
            )
            token = token_for_user(user.id, "mem_user", [Role.SALES])

        client = TestClient(make_test_app(chat_router))
        replies = ["第一轮回复", "第二轮回复（含合同信息）"]
        call_count = 0

        async def _mock_run(actor, user_input, with_audio=False):
            nonlocal call_count
            text = replies[min(call_count, len(replies) - 1)]
            call_count += 1
            state = {
                "current_intent": "crm_query",
                "customer_context": {"customer_name": "测试科技"},
                "turn_count": call_count,
            }
            memory_manager.save_history(
                actor.session_id,
                [
                    {"role": "user", "content": user_input, "channel": actor.channel},
                    {"role": "assistant", "content": text, "channel": actor.channel},
                ],
            )
            memory_manager.save_state(actor.session_id, state)
            return ChatPipelineResult(
                text=text,
                conversation_state=state,
                intent=state["current_intent"],
            )

        with patch(_CHAT_PIPELINE_PATCH, _mock_run):
            r1 = client.post(
                "/api/chat",
                headers=auth_headers(token),
                json={"message": "查一下测试科技联系方式"},
            )
            assert r1.status_code == 200
            sid = r1.json()["session_id"]

            r2 = client.post(
                "/api/chat",
                headers=auth_headers(token),
                json={"message": "合同金额呢", "session_id": sid},
            )
            assert r2.status_code == 200
            assert r2.json()["session_id"] == sid

        history = memory_manager.load_history(sid)
        roles = [m.role for m in history]
        assert "user" in roles and "assistant" in roles
        assert len(history) >= 4

    def test_history_survives_new_client(self, memory_db) -> None:
        # 场景：模拟重启后历史仍在 DB；输入：新 TestClient 同 session；预期：history 非空
        from main_server.core.auth.user_service import create_user
        from main_server.session.session_manager import session_manager
        from main_server.DB import db_session

        with db_session() as session:
            user = create_user(
                session,
                username="mem_restart",
                password="mem12345",
                roles=[Role.SALES],
            )
            user_id = user.id
            token = token_for_user(user_id, "mem_restart", [Role.SALES])

        session_info = session_manager.create(user_id, title="重启测试")
        sid = session_info.session_id
        memory_manager.save_history(
            sid,
            [
                {"role": "user", "content": "查一下测试科技", "channel": "text"},
                {"role": "assistant", "content": "联系方式是...", "channel": "text"},
            ],
        )
        memory_manager.save_state(sid, {"customer_context": {"customer_name": "测试科技"}})

        client = TestClient(make_test_app(chat_router))

        async def _mock_run(actor, user_input, with_audio=False):
            ctx = memory_manager.load_state(actor.session_id).get("customer_context") or {}
            name = ctx.get("customer_name", "")
            return ChatPipelineResult(
                text=f"上下文客户: {name}",
                conversation_state={"turn_count": 2},
            )

        with patch(_CHAT_PIPELINE_PATCH, _mock_run):
            resp = client.post(
                "/api/chat",
                headers=auth_headers(token),
                json={"message": "合同金额呢", "session_id": sid},
            )
            assert resp.status_code == 200
            assert "测试科技" in resp.json()["reply"]
