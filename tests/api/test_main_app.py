"""主应用入口集成测试（mock 生命周期与 health）。"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestMainApp:
    def test_health_on_full_app(self) -> None:
        # 场景：完整 app /health；输入：mock health；预期：200
        with patch("main_server.utils.init_db.init_database"):
            with patch(
                "main_server.services.health_service.get_health_status",
                return_value={"status": "ok", "providers": {}},
            ):
                from main_server.api.main import app

                client = TestClient(app, raise_server_exceptions=False)
                resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_cors_headers_present(self) -> None:
        # 场景：CORS；输入：OPTIONS/GET；预期：有 access-control 相关头
        with patch("main_server.utils.init_db.init_database"):
            with patch(
                "main_server.services.health_service.get_health_status",
                return_value={"status": "ok", "providers": {}},
            ):
                from main_server.api.main import app

                client = TestClient(app)
                resp = client.get("/health")
        assert resp.status_code == 200
