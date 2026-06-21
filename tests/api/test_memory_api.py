"""Memory API 测试（会话历史读取）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main_server.api.memory_api import router as memory_router
from main_server.api.session_api import router as session_router
from main_server.core.auth.permission import Role
from main_server.memory.memory_manager import memory_manager
from tests.conftest import auth_headers, make_test_app, token_for_user


@pytest.fixture
def memory_client(memory_db) -> TestClient:
    return TestClient(make_test_app(session_router, memory_router))


@pytest.fixture
def business_token(memory_db) -> str:
    from main_server.core.auth.user_service import create_user
    from main_server.DB import db_session

    with db_session() as session:
        user = create_user(
            session,
            username="mem_user",
            password="mem12345",
            roles=[Role.SALES],
        )
        return token_for_user(user.id, "mem_user", [Role.SALES])


class TestMemoryAPI:
    def test_get_session_messages(
        self, memory_client: TestClient, business_token: str
    ) -> None:
        create = memory_client.post(
            "/api/session",
            headers=auth_headers(business_token),
            json={"title": "历史测试"},
        )
        session_id = create.json()["session"]["session_id"]
        memory_manager.save_history(
            session_id,
            [
                {"role": "user", "content": "你好", "channel": "text"},
                {"role": "assistant", "content": "您好", "channel": "text"},
            ],
        )

        resp = memory_client.get(
            f"/api/session/{session_id}/messages",
            headers=auth_headers(business_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert data["total"] == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "你好"
        assert data["messages"][1]["role"] == "assistant"

    def test_get_messages_empty_session(
        self, memory_client: TestClient, business_token: str
    ) -> None:
        create = memory_client.post(
            "/api/session",
            headers=auth_headers(business_token),
            json={"title": "空会话"},
        )
        session_id = create.json()["session"]["session_id"]
        resp = memory_client.get(
            f"/api/session/{session_id}/messages",
            headers=auth_headers(business_token),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_cross_user_forbidden(
        self, memory_client: TestClient, memory_db
    ) -> None:
        from main_server.core.auth.user_service import create_user
        from main_server.DB import db_session

        with db_session() as session:
            u1 = create_user(
                session, username="m1", password="m1pass12", roles=[Role.SALES]
            )
            u2 = create_user(
                session, username="m2", password="m2pass12", roles=[Role.SALES]
            )
            t1 = token_for_user(u1.id, "m1", [Role.SALES])
            t2 = token_for_user(u2.id, "m2", [Role.SALES])

        create = memory_client.post(
            "/api/session",
            headers=auth_headers(t1),
            json={"title": "私有"},
        )
        sid = create.json()["session"]["session_id"]
        resp = memory_client.get(
            f"/api/session/{sid}/messages",
            headers=auth_headers(t2),
        )
        assert resp.status_code == 403

    def test_no_auth(self, memory_client: TestClient) -> None:
        resp = memory_client.get("/api/session/fake-id/messages")
        assert resp.status_code == 401
