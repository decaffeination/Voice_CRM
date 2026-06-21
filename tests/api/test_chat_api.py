"""Chat API 测试（mock Agent/TTS）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main_server.api.chat import router as chat_router
from main_server.core.auth.permission import Role
from tests.conftest import auth_headers, make_test_app, token_for_user


@pytest.fixture
def chat_client(memory_db, mock_agent_invoke, mock_tts) -> TestClient:
    mock_agent_invoke("你好，我是助手")
    return TestClient(make_test_app(chat_router))


@pytest.fixture
def sales_token(memory_db) -> str:
    from main_server.core.auth.user_service import create_user
    from main_server.DB import db_session

    with db_session() as session:
        user = create_user(
            session,
            username="chat_sales",
            password="chat1234",
            roles=[Role.SALES],
        )
        return token_for_user(user.id, "chat_sales", [Role.SALES])


class TestChatAPI:
    def test_chat_success(self, chat_client: TestClient, sales_token: str) -> None:
        # 场景：文本对话成功；输入：message；预期：reply + session_id
        resp = chat_client.post(
            "/api/chat",
            headers=auth_headers(sales_token),
            json={"message": "你好"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] == "你好，我是助手"
        assert data["session_id"]

    def test_chat_with_audio(self, chat_client: TestClient, sales_token: str) -> None:
        # 场景：带 TTS；输入：with_audio=True；预期：audio_base64 非空
        resp = chat_client.post(
            "/api/chat",
            headers=auth_headers(sales_token),
            json={"message": "播放语音", "with_audio": True},
        )
        assert resp.status_code == 200
        assert resp.json()["audio_base64"]

    def test_chat_reuses_session(self, chat_client: TestClient, sales_token: str) -> None:
        # 场景：复用 session_id；输入：两轮同 session；预期：session_id 相同
        r1 = chat_client.post(
            "/api/chat",
            headers=auth_headers(sales_token),
            json={"message": "第一轮"},
        )
        sid = r1.json()["session_id"]
        r2 = chat_client.post(
            "/api/chat",
            headers=auth_headers(sales_token),
            json={"message": "第二轮", "session_id": sid},
        )
        assert r2.json()["session_id"] == sid

    def test_empty_message(self, chat_client: TestClient, sales_token: str) -> None:
        # 场景：空消息；输入：message=""；预期：422
        resp = chat_client.post(
            "/api/chat",
            headers=auth_headers(sales_token),
            json={"message": ""},
        )
        assert resp.status_code == 422

    def test_missing_message(self, chat_client: TestClient, sales_token: str) -> None:
        # 场景：缺少 message；输入：空 body；预期：422
        resp = chat_client.post(
            "/api/chat",
            headers=auth_headers(sales_token),
            json={},
        )
        assert resp.status_code == 422

    def test_no_auth(self, chat_client: TestClient) -> None:
        # 场景：未鉴权；输入：无 token；预期：401
        resp = chat_client.post("/api/chat", json={"message": "hi"})
        assert resp.status_code == 401

    def test_special_chars_injection(
        self, chat_client: TestClient, sales_token: str
    ) -> None:
        # 场景：特殊字符；输入：<script>；预期：不崩溃，正常回复
        resp = chat_client.post(
            "/api/chat",
            headers=auth_headers(sales_token),
            json={"message": "<script>alert(1)</script> DROP TABLE"},
        )
        assert resp.status_code == 200

    def test_first_message_auto_title(
        self, chat_client: TestClient, sales_token: str
    ) -> None:
        # 场景：首条消息自动标题；输入：新会话首条消息；预期：session_title 返回
        resp = chat_client.post(
            "/api/chat",
            headers=auth_headers(sales_token),
            json={"message": "查询客户信息"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_title"] == "查询客户信息"
        sid = data["session_id"]

        follow_up = chat_client.post(
            "/api/chat",
            headers=auth_headers(sales_token),
            json={"message": "继续", "session_id": sid},
        )
        assert follow_up.status_code == 200
        assert follow_up.json().get("session_title") is None
