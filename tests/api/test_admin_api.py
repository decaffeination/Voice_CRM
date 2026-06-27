"""审计持久化与管理设置 API 测试。"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from main_server.api.audit_api import router as audit_router
from main_server.api.settings_api import router as settings_router
from main_server.core.audit import audit_log
from main_server.core.auth.jwt_auth import create_access_token
from main_server.core.auth.permission import Role
from main_server.core.auth.user_service import create_user
from main_server.core.exception_handlers import register_exception_handlers
from main_server.DB import db_session
from main_server.services.audit_service import list_audit_logs
from main_server.services.runtime_settings import runtime_settings


@pytest.fixture(autouse=True)
def reset_runtime_settings() -> None:
    runtime_settings.clear_all_overrides()
    yield
    runtime_settings.clear_all_overrides()


@pytest.fixture
def admin_client(memory_db) -> TestClient:
    with db_session() as session:
        admin = create_user(
            session,
            username="admin2",
            password="admin123",
            roles=[Role.ADMIN],
        )
        admin_id = admin.id
        sales = create_user(
            session,
            username="sales_audit",
            password="sales123",
            roles=[Role.SALES],
        )
        sales_id = sales.id

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(audit_router)
    app.include_router(settings_router)

    client = TestClient(app)
    client.admin_token = create_access_token(  # type: ignore[attr-defined]
        user_id=admin_id, username="admin2", roles=[Role.ADMIN]
    )
    client.sales_token = create_access_token(  # type: ignore[attr-defined]
        user_id=sales_id, username="sales_audit", roles=[Role.SALES]
    )
    return client


class TestAuditPersistence:
    def test_audit_log_persisted(self, memory_db) -> None:
        audit_log("crm.lookup", resource="customer", detail="name=测试")
        items, total = list_audit_logs(action="crm.lookup", limit=10)
        assert total == 1
        assert items[0]["action"] == "crm.lookup"
        assert "name=测试" in items[0]["detail"]


class TestAuditAPI:
    def test_admin_can_list_audit(self, admin_client: TestClient) -> None:
        audit_log("settings.email_update", resource="email", detail="test")
        resp = admin_client.get(
            "/api/admin/audit",
            headers={"Authorization": f"Bearer {admin_client.admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_non_admin_forbidden(self, admin_client: TestClient) -> None:
        resp = admin_client.get(
            "/api/admin/audit",
            headers={"Authorization": f"Bearer {admin_client.sales_token}"},
        )
        assert resp.status_code == 403


class TestEmailSettingsAPI:
    def test_get_and_update_email_settings(self, admin_client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {admin_client.admin_token}"}
        get_resp = admin_client.get("/api/admin/settings/email", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["dry_run"] is True

        patch_resp = admin_client.patch(
            "/api/admin/settings/email",
            headers=headers,
            json={"dry_run": False, "enabled": True},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["dry_run"] is False

        config = runtime_settings.get_email_public_config()
        assert config["dry_run"] is False

    def test_sales_cannot_update_settings(self, admin_client: TestClient) -> None:
        resp = admin_client.patch(
            "/api/admin/settings/email",
            headers={"Authorization": f"Bearer {admin_client.sales_token}"},
            json={"dry_run": True},
        )
        assert resp.status_code == 403


class TestSmtpSettingsAPI:
    def test_update_smtp_and_test_send(self, admin_client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {admin_client.admin_token}"}
        patch_resp = admin_client.patch(
            "/api/admin/settings/email/smtp",
            headers=headers,
            json={
                "smtp_host": "smtp.test.local",
                "smtp_port": 587,
                "smtp_user": "user@test.local",
                "smtp_password": "secret",
                "from_address": "noreply@test.local",
                "use_tls": True,
            },
        )
        assert patch_resp.status_code == 200
        body = patch_resp.json()
        assert body["smtp_host"] == "smtp.test.local"
        assert body["smtp_password_set"] is True
        assert "secret" not in str(body)

        test_resp = admin_client.post(
            "/api/admin/settings/email/test",
            headers=headers,
            json={"to": "admin@test.local"},
        )
        assert test_resp.status_code == 200
        assert test_resp.json()["sent"] is True


class TestSystemSettingsAPI:
    def test_get_and_update_system_params(self, admin_client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {admin_client.admin_token}"}
        get_resp = admin_client.get("/api/admin/settings/system", headers=headers)
        assert get_resp.status_code == 200
        assert "system_name" in get_resp.json()

        patch_resp = admin_client.patch(
            "/api/admin/settings/system",
            headers=headers,
            json={"system_name": "测试 CRM", "token_limit": 4096},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["system_name"] == "测试 CRM"
        assert patch_resp.json()["token_limit"] == 4096


class TestModelSettingsAPI:
    def test_get_and_update_models(self, admin_client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {admin_client.admin_token}"}
        get_resp = admin_client.get("/api/admin/settings/models", headers=headers)
        assert get_resp.status_code == 200
        items = get_resp.json()["items"]
        assert len(items) >= 1
        assert items[0]["provider"]

        patch_resp = admin_client.patch(
            "/api/admin/settings/models",
            headers=headers,
            json={"temperature": 0.5, "max_tokens": 2048},
        )
        assert patch_resp.status_code == 200
        updated = patch_resp.json()["items"][0]
        assert updated["temperature"] == 0.5
        assert updated["max_tokens"] == 2048
