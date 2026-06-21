"""CRM 访问范围（access_control）单元测试。"""

from __future__ import annotations

import pytest

from main_server.core.auth.access_control import (
    assert_customer_access,
    can_view_employee_customers,
    get_team_user_ids,
    resolve_customer_access_scope,
)
from main_server.core.auth.permission import Role
from main_server.core.exceptions import PermissionDeniedError
from main_server.CRM.writes.curstomer_write import create_customer
from main_server.DB import db_session
from main_server.DB.models import Customer


class TestAccessScope:
    def test_admin_sees_all(self, memory_db_team) -> None:
        # 场景：Admin 全量；输入：admin 角色；预期：mode=all
        users = memory_db_team["users"]
        with db_session() as session:
            scope = resolve_customer_access_scope(
                session, users["manager"].id, [Role.ADMIN]
            )
            assert scope.mode == "all"

    def test_sales_manager_team_scope(self, memory_db_team) -> None:
        # 场景：经理团队视图；输入：SalesManager；预期：mode=team
        users = memory_db_team["users"]
        with db_session() as session:
            scope = resolve_customer_access_scope(
                session, users["manager"].id, [Role.SALES_MANAGER]
            )
            assert scope.mode == "team"
            assert users["sales_a"].id in scope.team_user_ids
            assert users["sales_b"].id in scope.team_user_ids

    def test_sales_owner_scope(self, memory_db_team) -> None:
        # 场景：销售仅自己；输入：Sales；预期：mode=owner
        users = memory_db_team["users"]
        with db_session() as session:
            scope = resolve_customer_access_scope(
                session, users["sales_a"].id, [Role.SALES]
            )
            assert scope.mode == "owner"
            assert scope.owner_user_id == users["sales_a"].id

    def test_assert_customer_access_denied(self, memory_db_team) -> None:
        # 场景：越权访问客户；输入：sales_a 访问外区客户；预期：PermissionDeniedError
        users = memory_db_team["users"]
        with db_session() as session:
            other_customer = (
                session.query(Customer)
                .filter(Customer.name == "外区客户")
                .first()
            )
            assert other_customer is not None
            with pytest.raises(PermissionDeniedError, match="无权"):
                assert_customer_access(
                    session,
                    other_customer,
                    users["sales_a"].id,
                    [Role.SALES],
                )

    def test_get_team_user_ids(self, memory_db_team) -> None:
        # 场景：同部门 user_id；输入：经理；预期：含 sales_a/sales_b
        users = memory_db_team["users"]
        with db_session() as session:
            team_ids = get_team_user_ids(session, users["manager"].id)
            assert users["sales_a"].id in team_ids
            assert users["sales_b"].id in team_ids
            assert users["other_sales"].id not in team_ids

    def test_can_view_employee_customers(self, memory_db_team) -> None:
        # 场景：经理查看团队成员；输入：manager 看 sales_a；预期：True
        users = memory_db_team["users"]
        with db_session() as session:
            assert can_view_employee_customers(
                session,
                viewer_user_id=users["manager"].id,
                target_employee_user_id=users["sales_a"].id,
                roles=[Role.SALES_MANAGER],
            )
            assert not can_view_employee_customers(
                session,
                viewer_user_id=users["sales_a"].id,
                target_employee_user_id=users["other_sales"].id,
                roles=[Role.SALES],
            )
