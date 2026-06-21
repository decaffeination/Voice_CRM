"""Health 检查 API 测试。"""

from __future__ import annotations

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _health_app() -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    def health_check():
        from main_server.services.health_service import get_health_status

        return get_health_status()

    return app


class TestHealthAPI:
    def test_health_returns_status(self) -> None:
        # 场景：健康检查；输入：GET /health；预期：含 status 字段
        with patch(
            "main_server.services.health_service.get_health_status",
            return_value={"status": "ok", "providers": {}},
        ):
            client = TestClient(_health_app())
            resp = client.get("/health")
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"

    def test_health_degraded(self) -> None:
        # 场景：降级状态；输入：mock degraded；预期：status=degraded
        with patch(
            "main_server.services.health_service.get_health_status",
            return_value={"status": "degraded", "providers": {"llm": "down"}},
        ):
            client = TestClient(_health_app())
            resp = client.get("/health")
            assert resp.json()["status"] == "degraded"
