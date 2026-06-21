"""会话 API 测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main_server.api.session_api import router as session_router
from main_server.core.auth.permission import Role
from tests.conftest import auth_headers, login_token, make_test_app, token_for_user


@pytest.fixture
def session_client(memory_db) -> TestClient:
    return TestClient(make_test_app(session_router))


@pytest.fixture
def business_token(memory_db) -> str:
    from main_server.core.auth.user_service import create_user
    from main_server.DB import db_session

    with db_session() as session:
        user = create_user(
            session,
            username="biz_user",
            password="biz12345",
            roles=[Role.SALES],
        )
        return token_for_user(user.id, "biz_user", [Role.SALES])


class TestSessionAPI:
    def test_create_session(self, session_client: TestClient, business_token: str) -> None:
        # 场景：创建会话；输入：title；预期：返回 session_id
        resp = session_client.post(
            "/api/session",
            headers=auth_headers(business_token),
            json={"title": "我的会话"},
        )
        assert resp.status_code == 200
        assert resp.json()["session"]["title"] == "我的会话"

    def test_list_sessions(self, session_client: TestClient, business_token: str) -> None:
        # 场景：列表；输入：创建后 list；预期：total>=1
        session_client.post(
            "/api/session",
            headers=auth_headers(business_token),
            json={"title": "列表测试"},
        )
        resp = session_client.get(
            "/api/sessions",
            headers=auth_headers(business_token),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_get_session(self, session_client: TestClient, business_token: str) -> None:
        # 场景：获取详情；输入：有效 session_id；预期：200
        create = session_client.post(
            "/api/session",
            headers=auth_headers(business_token),
            json={"title": "详情"},
        )
        sid = create.json()["session"]["session_id"]
        resp = session_client.get(
            f"/api/session/{sid}",
            headers=auth_headers(business_token),
        )
        assert resp.status_code == 200

    def test_delete_session(self, session_client: TestClient, business_token: str) -> None:
        # 场景：删除；输入：有效 session；预期：200 + memory 统计
        create = session_client.post(
            "/api/session",
            headers=auth_headers(business_token),
            json={"title": "待删"},
        )
        sid = create.json()["session"]["session_id"]
        resp = session_client.delete(
            f"/api/session/{sid}",
            headers=auth_headers(business_token),
        )
        assert resp.status_code == 200
        get_resp = session_client.get(
            f"/api/session/{sid}",
            headers=auth_headers(business_token),
        )
        assert get_resp.status_code == 404

    def test_cross_user_forbidden(
        self, session_client: TestClient, memory_db
    ) -> None:
        # 场景：越权访问会话；输入：user2 访问 user1 会话；预期：403
        from main_server.core.auth.user_service import create_user
        from main_server.DB import db_session

        with db_session() as session:
            u1 = create_user(
                session, username="u1", password="u1pass12", roles=[Role.SALES]
            )
            u2 = create_user(
                session, username="u2", password="u2pass12", roles=[Role.SALES]
            )
            t1 = token_for_user(u1.id, "u1", [Role.SALES])
            t2 = token_for_user(u2.id, "u2", [Role.SALES])

        create = session_client.post(
            "/api/session",
            headers=auth_headers(t1),
            json={"title": "私有"},
        )
        sid = create.json()["session"]["session_id"]
        resp = session_client.get(
            f"/api/session/{sid}",
            headers=auth_headers(t2),
        )
        assert resp.status_code == 403

    def test_no_auth(self, session_client: TestClient) -> None:
        # 场景：未鉴权；输入：无 token；预期：401
        resp = session_client.get("/api/sessions")
        assert resp.status_code == 401

    def test_title_too_long(self, session_client: TestClient, business_token: str) -> None:
        # 场景：超长 title；输入：256 字符；预期：422
        resp = session_client.post(
            "/api/session",
            headers=auth_headers(business_token),
            json={"title": "x" * 256},
        )
        assert resp.status_code == 422
