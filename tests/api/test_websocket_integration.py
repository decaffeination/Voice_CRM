"""WebSocket 基础集成测试。"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main_server.api.websocket.audio_ws import router as ws_router
from main_server.core.auth.permission import Role
from main_server.core.auth.user_service import create_user
from main_server.DB import db_session
from main_server.session.session_manager import session_manager
from tests.conftest import make_test_app, token_for_user


@pytest.fixture
def ws_client(memory_db) -> TestClient:
    return TestClient(make_test_app(ws_router))


@pytest.fixture
def sales_ws_context(memory_db) -> tuple[str, str]:
    with db_session() as session:
        user = create_user(
            session,
            username="ws_sales",
            password="ws123456",
            roles=[Role.SALES],
        )
        user_id = user.id
    token = token_for_user(user_id, "ws_sales", [Role.SALES])
    chat_session = session_manager.create(user_id, title="WS 测试")
    return token, chat_session.session_id


class TestWebSocketIntegration:
    def test_ws_rejects_invalid_token(self, ws_client: TestClient) -> None:
        with ws_client.websocket_connect(
            "/ws/audio/fake-session?token=invalid.token.here"
        ) as ws:
            payload = ws.receive_json()
            assert payload["type"] == "error"
            assert payload.get("stage") == "auth"

    def test_ws_ping_pong(self, ws_client: TestClient, sales_ws_context: tuple[str, str]) -> None:
        token, session_id = sales_ws_context
        with patch(
            "main_server.services.voice_services.ws_service.resolve_provider_timeout",
            return_value=30.0,
        ):
            with ws_client.websocket_connect(
                f"/ws/audio/{session_id}?token={token}"
            ) as ws:
                ready = ws.receive_json()
                assert ready["type"] == "ready"
                assert ready["session_id"] == session_id

                ws.send_json({"type": "ping"})
                pong = ws.receive_json()
                assert pong["type"] == "pong"

    def test_ws_rejects_foreign_session(
        self, ws_client: TestClient, sales_ws_context: tuple[str, str], memory_db
    ) -> None:
        _, session_id = sales_ws_context
        with db_session() as session:
            other = create_user(
                session,
                username="ws_other",
                password="other1234",
                roles=[Role.SALES],
            )
            other_id = other.id
        other_token = token_for_user(other_id, "ws_other", [Role.SALES])

        with ws_client.websocket_connect(
            f"/ws/audio/{session_id}?token={other_token}"
        ) as ws:
            payload = ws.receive_json()
            assert payload["type"] == "error"
            assert payload.get("stage") == "session"
