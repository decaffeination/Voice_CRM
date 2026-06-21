"""CRM API 测试：RBAC、参数边界、越权。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main_server.api.crm_api import router as crm_router
from main_server.core.auth.permission import Role
from tests.conftest import auth_headers, make_test_app, token_for_user


@pytest.fixture
def crm_client(memory_db_team) -> TestClient:
    return TestClient(make_test_app(crm_router))


class TestCRMListCustomers:
    def test_admin_lists_all(self, crm_client: TestClient, memory_db_team) -> None:
        # 场景：Admin 列表；输入：admin token；预期：含团队客户
        token = token_for_user(1, "admin", [Role.ADMIN])
        resp = crm_client.get(
            "/api/crm/customers",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        names = {c["name"] for c in resp.json()["customers"]}
        assert "团队客户甲" in names

    def test_sales_sees_own_only(self, crm_client: TestClient, memory_db_team) -> None:
        # 场景：销售仅看自己；输入：sales_a；预期：不含外区客户
        users = memory_db_team["users"]
        token = token_for_user(
            users["sales_a"].id, "sales_a", [Role.SALES]
        )
        resp = crm_client.get(
            "/api/crm/customers",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        names = {c["name"] for c in resp.json()["customers"]}
        assert "团队客户甲" in names
        assert "外区客户" not in names

    def test_manager_sees_team(self, crm_client: TestClient, memory_db_team) -> None:
        # 场景：经理看团队；输入：SalesManager；预期：含甲乙不含外区
        users = memory_db_team["users"]
        token = token_for_user(
            users["manager"].id, "mgr1", [Role.SALES_MANAGER]
        )
        resp = crm_client.get(
            "/api/crm/customers",
            headers=auth_headers(token),
        )
        names = {c["name"] for c in resp.json()["customers"]}
        assert "团队客户甲" in names
        assert "团队客户乙" in names
        assert "外区客户" not in names

    def test_limit_boundary(self, crm_client: TestClient, memory_db_team) -> None:
        # 场景：分页 limit 边界；输入：limit=0；预期：422
        users = memory_db_team["users"]
        token = token_for_user(users["manager"].id, "mgr1", [Role.ADMIN])
        resp = crm_client.get(
            "/api/crm/customers?limit=0",
            headers=auth_headers(token),
        )
        assert resp.status_code == 422

    def test_limit_max_boundary(self, crm_client: TestClient, memory_db_team) -> None:
        # 场景：limit 超限；输入：limit=201；预期：422
        users = memory_db_team["users"]
        token = token_for_user(users["manager"].id, "mgr1", [Role.ADMIN])
        resp = crm_client.get(
            "/api/crm/customers?limit=201",
            headers=auth_headers(token),
        )
        assert resp.status_code == 422

    def test_no_auth(self, crm_client: TestClient) -> None:
        # 场景：未鉴权；输入：无 token；预期：401
        resp = crm_client.get("/api/crm/customers")
        assert resp.status_code == 401


class TestCRMLookup:
    def test_lookup_found(self, crm_client: TestClient, memory_db_team) -> None:
        # 场景：按名查找；输入：团队客户甲；预期：found=True
        users = memory_db_team["users"]
        token = token_for_user(users["sales_a"].id, "sales_a", [Role.SALES])
        resp = crm_client.get(
            "/api/crm/customers/lookup?name=团队客户甲",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["found"]

    def test_lookup_missing_name(self, crm_client: TestClient, memory_db_team) -> None:
        # 场景：缺少 name；输入：无 query；预期：422
        users = memory_db_team["users"]
        token = token_for_user(users["sales_a"].id, "sales_a", [Role.SALES])
        resp = crm_client.get(
            "/api/crm/customers/lookup",
            headers=auth_headers(token),
        )
        assert resp.status_code == 422

    def test_lookup_special_chars(self, crm_client: TestClient, memory_db_team) -> None:
        # 场景：特殊字符注入；输入：<script>；预期：不崩溃，found=False
        users = memory_db_team["users"]
        token = token_for_user(users["sales_a"].id, "sales_a", [Role.SALES])
        resp = crm_client.get(
            "/api/crm/customers/lookup?name=<script>alert(1)</script>",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert not resp.json()["found"]


class TestCRMGetCustomer:
    def test_cross_team_forbidden(
        self, crm_client: TestClient, memory_db_team
    ) -> None:
        # 场景：越权访问客户详情；输入：sales_a 访问外区客户；预期：403
        from main_server.DB import db_session
        from main_server.DB.models import Customer

        users = memory_db_team["users"]
        with db_session() as session:
            other = (
                session.query(Customer).filter(Customer.name == "外区客户").first()
            )
            assert other is not None
            cid = other.id

        token = token_for_user(users["sales_a"].id, "sales_a", [Role.SALES])
        resp = crm_client.get(
            f"/api/crm/customers/{cid}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_not_found(self, crm_client: TestClient, memory_db_team) -> None:
        # 场景：客户不存在；输入：id=99999；预期：404
        users = memory_db_team["users"]
        token = token_for_user(users["manager"].id, "mgr1", [Role.ADMIN])
        resp = crm_client.get(
            "/api/crm/customers/99999",
            headers=auth_headers(token),
        )
        assert resp.status_code == 404


class TestCRMProfileAndRelated:
    def test_customer_profile(self, crm_client: TestClient, memory_db_team) -> None:
        # 场景：客户档案；输入：团队客户甲；预期：200 + customer
        from main_server.DB import db_session
        from main_server.DB.models import Customer

        users = memory_db_team["users"]
        with db_session() as session:
            customer = (
                session.query(Customer).filter(Customer.name == "团队客户甲").first()
            )
            assert customer is not None
            cid = customer.id

        token = token_for_user(users["sales_a"].id, "sales_a", [Role.SALES])
        resp = crm_client.get(
            f"/api/crm/customers/{cid}/profile",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200

    def test_list_followups(self, crm_client: TestClient, memory_db_team) -> None:
        # 场景：跟进列表；输入：有效 customer_id；预期：200
        from main_server.DB import db_session
        from main_server.DB.models import Customer

        users = memory_db_team["users"]
        with db_session() as session:
            customer = (
                session.query(Customer).filter(Customer.name == "团队客户甲").first()
            )
            assert customer is not None
            cid = customer.id

        token = token_for_user(users["sales_a"].id, "sales_a", [Role.SALES])
        resp = crm_client.get(
            f"/api/crm/customers/{cid}/followups",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200

    def test_recent_updates(self, crm_client: TestClient, memory_db_team) -> None:
        # 场景：近期更新；输入：days=7；预期：200 + customers
        users = memory_db_team["users"]
        token = token_for_user(users["manager"].id, "mgr1", [Role.ADMIN])
        resp = crm_client.get(
            "/api/crm/recent-updates?days=7",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert "customers" in resp.json()

    def test_recent_updates_days_boundary(
        self, crm_client: TestClient, memory_db_team
    ) -> None:
        # 场景：days 超限；输入：days=0；预期：422
        users = memory_db_team["users"]
        token = token_for_user(users["manager"].id, "mgr1", [Role.ADMIN])
        resp = crm_client.get(
            "/api/crm/recent-updates?days=0",
            headers=auth_headers(token),
        )
        assert resp.status_code == 422
