"""Dashboard API 测试。"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main_server.api.dashboard_api import router as dashboard_router
from main_server.core.auth.permission import Role
from main_server.core.auth.user_service import create_user
from main_server.DB import db_session
from tests.conftest import auth_headers, make_test_app, token_for_user


@pytest.fixture
def dashboard_client(memory_db) -> TestClient:
    return TestClient(make_test_app(dashboard_router))


@pytest.fixture
def sales_token(memory_db) -> str:
    with db_session() as session:
        user = create_user(
            session,
            username="dash_sales",
            password="dash12345",
            roles=[Role.SALES],
        )
        return token_for_user(user.id, "dash_sales", [Role.SALES])


@pytest.fixture
def mock_dashboard_knowledge():
    kb_stats = {
        "document_count": 2,
        "chunk_count": 10,
        "last_updated": None,
        "kb_status": "ok",
    }
    with patch(
        "main_server.services.dashboard_service.knowledge_service.stats",
        return_value=kb_stats,
    ), patch(
        "main_server.services.dashboard_service.list_knowledge_docs",
        return_value=[],
    ), patch(
        "main_server.services.dashboard_service.get_health_status",
        return_value={"status": "ok", "providers": {}},
    ):
        yield


class TestDashboardAPI:
    def test_overview_requires_auth(self, dashboard_client: TestClient) -> None:
        resp = dashboard_client.get("/api/dashboard/overview")
        assert resp.status_code == 401

    def test_overview_success(
        self,
        dashboard_client: TestClient,
        sales_token: str,
        mock_dashboard_knowledge,
    ) -> None:
        resp = dashboard_client.get(
            "/api/dashboard/overview",
            headers=auth_headers(sales_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "overview" in data
        assert "ai_runtime" in data
        assert "knowledge" in data
        assert "crm" in data
        assert "recent_activities" in data
        assert "system_status" in data
        assert isinstance(data["system_status"], list)

    def test_overview_contains_session_stats(
        self,
        dashboard_client: TestClient,
        sales_token: str,
        mock_dashboard_knowledge,
    ) -> None:
        resp = dashboard_client.get(
            "/api/dashboard/overview",
            headers=auth_headers(sales_token),
        )
        overview = resp.json()["overview"]
        assert "total_sessions" in overview
        assert "today_sessions" in overview
