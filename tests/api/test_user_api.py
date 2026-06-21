"""用户 API 测试：鉴权、参数校验、CRUD。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main_server.api.user_api import router as user_router
from main_server.core.auth.auth_service import authenticate
from main_server.core.auth.permission import Role
from main_server.core.auth.user_service import create_user
from main_server.core.exceptions import AuthError
from main_server.DB import db_session
from main_server.DB.models import User
from tests.conftest import login_token, make_test_app


@pytest.fixture
def user_client(memory_db) -> TestClient:
    return TestClient(make_test_app(user_router, prefix="/api"))


class TestLoginAPI:
    def test_login_success(self, user_client: TestClient) -> None:
        # 场景：正确凭据登录；输入：admin/admin123；预期：200 + token
        resp = user_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, user_client: TestClient) -> None:
        # 场景：密码错误；输入：错误密码；预期：401
        resp = user_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self, user_client: TestClient) -> None:
        # 场景：缺少必填；输入：仅 username；预期：422
        resp = user_client.post("/api/auth/login", json={"username": "admin"})
        assert resp.status_code == 422


class TestMeAPI:
    def test_me_requires_auth(self, user_client: TestClient) -> None:
        # 场景：未鉴权；输入：无 token；预期：401
        resp = user_client.get("/api/me")
        assert resp.status_code == 401

    def test_me_success(self, user_client: TestClient) -> None:
        # 场景：获取当前用户；输入：有效 token；预期：username=admin
        token = login_token(user_client)
        resp = user_client.get(
            "/api/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"
        assert Role.ADMIN in resp.json()["roles"]


class TestUserCRUD:
    def test_create_user_admin_only(self, user_client: TestClient) -> None:
        # 场景：Admin 创建用户；输入：sales 角色；预期：200
        token = login_token(user_client)
        resp = user_client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "sales1",
                "password": "sales123",
                "display_name": "销售一号",
                "roles": [Role.SALES],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == "sales1"

    def test_non_admin_cannot_create(self, user_client: TestClient, memory_db) -> None:
        # 场景：非 Admin 创建用户；输入：sales token；预期：403
        from main_server.core.auth.user_service import create_user
        from main_server.DB import db_session

        with db_session() as session:
            create_user(
                session,
                username="sales1",
                password="sales123",
                roles=[Role.SALES],
            )
        sales_token = login_token(user_client, "sales1", "sales123")
        resp = user_client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {sales_token}"},
            json={"username": "x", "password": "x123456", "roles": [Role.SALES]},
        )
        assert resp.status_code == 403

    def test_create_duplicate_username(self, user_client: TestClient) -> None:
        # 场景：重复用户名；输入：admin 已存在；预期：4xx
        token = login_token(user_client)
        resp = user_client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "admin",
                "password": "admin123",
                "roles": [Role.ADMIN],
            },
        )
        assert resp.status_code in (400, 409, 422)

    def test_update_roles(self, user_client: TestClient) -> None:
        # 场景：更新角色；输入：patch roles；预期：角色列表更新
        token = login_token(user_client)
        create_resp = user_client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "cs1",
                "password": "cs123456",
                "roles": [Role.CUSTOMER_SERVICE],
            },
        )
        user_id = create_resp.json()["user_id"]
        patch_resp = user_client.patch(
            f"/api/users/{user_id}/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={"roles": [Role.CUSTOMER_SERVICE, Role.SALES]},
        )
        assert patch_resp.status_code == 200
        assert set(patch_resp.json()["roles"]) == {
            Role.CUSTOMER_SERVICE,
            Role.SALES,
        }

    def test_change_password(self, user_client: TestClient) -> None:
        # 场景：用户改密；输入：旧密+新密；预期：新密可登录
        token = login_token(user_client)
        user_client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"username": "pwuser", "password": "oldpass1", "roles": [Role.SALES]},
        )
        user_token = login_token(user_client, "pwuser", "oldpass1")
        resp = user_client.put(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"old_password": "oldpass1", "new_password": "newpass1"},
        )
        assert resp.status_code == 200
        login_token(user_client, "pwuser", "newpass1")

    def test_list_roles_public(self, user_client: TestClient) -> None:
        # 场景：角色列表；输入：无鉴权；预期：4 个角色
        resp = user_client.get("/api/roles")
        assert resp.status_code == 200
        codes = {item["code"] for item in resp.json()}
        assert codes == set(Role.ALL)

    def test_list_users_admin_only(self, user_client: TestClient) -> None:
        token = login_token(user_client)
        resp = user_client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(item["username"] == "admin" for item in data["items"])

    def test_non_admin_cannot_list_users(
        self, user_client: TestClient, memory_db
    ) -> None:
        with db_session() as session:
            create_user(
                session,
                username="sales_list",
                password="sales123",
                roles=[Role.SALES],
            )
        sales_token = login_token(user_client, "sales_list", "sales123")
        resp = user_client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {sales_token}"},
        )
        assert resp.status_code == 403

    def test_update_user_profile_and_status(self, user_client: TestClient) -> None:
        token = login_token(user_client)
        create_resp = user_client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "editme",
                "password": "edit1234",
                "display_name": "待编辑",
                "roles": [Role.SALES],
            },
        )
        user_id = create_resp.json()["user_id"]

        patch_resp = user_client.patch(
            f"/api/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"display_name": "已编辑", "is_active": False},
        )
        assert patch_resp.status_code == 200
        body = patch_resp.json()
        assert body["display_name"] == "已编辑"
        assert body["is_active"] is False

    def test_delete_user(self, user_client: TestClient) -> None:
        token = login_token(user_client)
        create_resp = user_client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "todelete",
                "password": "delete12",
                "roles": [Role.SALES],
            },
        )
        user_id = create_resp.json()["user_id"]
        delete_resp = user_client.delete(
            f"/api/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete_resp.status_code == 200
        list_resp = user_client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        usernames = [item["username"] for item in list_resp.json()["items"]]
        assert "todelete" not in usernames

    def test_cannot_delete_self(self, user_client: TestClient) -> None:
        token = login_token(user_client)
        me_resp = user_client.get(
            "/api/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        user_id = me_resp.json()["user_id"]
        resp = user_client.delete(
            f"/api/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_cannot_delete_last_admin(self, user_client: TestClient) -> None:
        token = login_token(user_client)
        me_resp = user_client.get(
            "/api/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        admin_id = me_resp.json()["user_id"]
        user_client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "onlysales",
                "password": "sales123",
                "roles": [Role.SALES],
            },
        )
        resp = user_client.delete(
            f"/api/users/{admin_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_list_users_filter_by_role(self, user_client: TestClient) -> None:
        token = login_token(user_client)
        user_client.post(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "filter_sales",
                "password": "sales123",
                "roles": [Role.SALES],
            },
        )
        resp = user_client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
            params={"role": Role.SALES},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert Role.SALES in item["roles"]

    def test_cannot_demote_last_admin(self, user_client: TestClient) -> None:
        token = login_token(user_client)
        me_resp = user_client.get(
            "/api/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        admin_id = me_resp.json()["user_id"]
        resp = user_client.patch(
            f"/api/users/{admin_id}/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={"roles": [Role.SALES]},
        )
        assert resp.status_code == 403


class TestUserService:
    def test_authenticate_inactive_user(self, memory_db) -> None:
        # 场景：停用用户登录；输入：is_active=0；预期：AuthError
        with db_session() as session:
            create_user(
                session,
                username="inactive_user",
                password="pass1234",
                roles=[Role.SALES],
            )
            user = session.query(User).filter(User.username == "inactive_user").first()
            assert user is not None
            user.is_active = False
            session.flush()
            with pytest.raises(AuthError, match="停用"):
                authenticate(session, "inactive_user", "pass1234")
