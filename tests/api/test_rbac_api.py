"""RBAC API 测试。"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from main_server.api.rbac_api import router as rbac_router
from main_server.core.auth.jwt_auth import create_access_token
from main_server.core.auth.permission import Role
from main_server.core.auth.user_service import create_user
from main_server.core.exception_handlers import register_exception_handlers
from main_server.DB import db_session
from main_server.services.rbac_service import seed_permissions, seed_role_permissions


@pytest.fixture(autouse=True)
def seed_rbac(memory_db) -> None:
    seed_permissions()
    seed_role_permissions()


@pytest.fixture
def rbac_client(memory_db) -> TestClient:
    with db_session() as session:
        admin = create_user(
            session,
            username="rbac_admin",
            password="admin123",
            roles=[Role.ADMIN],
        )
        admin_id = admin.id
        sales = create_user(
            session,
            username="rbac_sales",
            password="sales123",
            roles=[Role.SALES],
        )
        sales_id = sales.id

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(rbac_router)

    client = TestClient(app)
    client.admin_token = create_access_token(  # type: ignore[attr-defined]
        user_id=admin_id, username="rbac_admin", roles=[Role.ADMIN]
    )
    client.sales_token = create_access_token(  # type: ignore[attr-defined]
        user_id=sales_id, username="rbac_sales", roles=[Role.SALES]
    )
    return client


class TestRBACAPI:
    def test_permission_tree(self, rbac_client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {rbac_client.admin_token}"}
        resp = rbac_client.get("/api/admin/permissions/tree", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(node["key"] == "crm" for node in items)

    def test_get_and_update_role_permissions(self, rbac_client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {rbac_client.admin_token}"}
        get_resp = rbac_client.get(
            "/api/admin/roles/Sales/permissions",
            headers=headers,
        )
        assert get_resp.status_code == 200
        assert "crm.read" in get_resp.json()["permission_codes"]

        patch_resp = rbac_client.patch(
            "/api/admin/roles/Sales/permissions",
            headers=headers,
            json={"permission_codes": ["ai.chat", "crm.read"]},
        )
        assert patch_resp.status_code == 200
        assert set(patch_resp.json()["permission_codes"]) == {"ai.chat", "crm.read"}

        verify = rbac_client.get(
            "/api/admin/roles/Sales/permissions",
            headers=headers,
        )
        assert set(verify.json()["permission_codes"]) == {"ai.chat", "crm.read"}

    def test_admin_cannot_drop_required_permissions(self, rbac_client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {rbac_client.admin_token}"}
        resp = rbac_client.patch(
            "/api/admin/roles/Admin/permissions",
            headers=headers,
            json={"permission_codes": ["ai.chat"]},
        )
        assert resp.status_code == 400

    def test_non_admin_forbidden(self, rbac_client: TestClient) -> None:
        headers = {"Authorization": f"Bearer {rbac_client.sales_token}"}
        resp = rbac_client.get("/api/admin/permissions/tree", headers=headers)
        assert resp.status_code == 403
