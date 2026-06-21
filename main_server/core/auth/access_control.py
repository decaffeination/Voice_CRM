"""CRM 与业务资源的访问范围解析（RBAC 业务层）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from main_server.core.auth.permission import Role, load_user_with_roles, role_codes
from main_server.core.exceptions import PermissionDeniedError
from main_server.DB.models import Customer, Employee


AccessMode = Literal["all", "team", "owner"]


@dataclass(frozen=True)
class CustomerAccessScope:
    """客户数据可见范围。"""

    mode: AccessMode
    owner_user_id: int | None = None
    team_user_ids: tuple[int, ...] = ()

    def owner_filter_kwargs(self) -> dict:
        """供 customer_repo 使用的 owner 过滤参数。"""
        if self.mode == "all":
            return {}
        if self.mode == "owner" and self.owner_user_id is not None:
            return {"owner_user_id": self.owner_user_id}
        if self.mode == "team" and self.team_user_ids:
            return {"owner_user_ids": list(self.team_user_ids)}
        if self.owner_user_id is not None:
            return {"owner_user_id": self.owner_user_id}
        return {"owner_user_ids": []}


def resolve_roles(
    session: Session,
    user_id: int | None,
    roles: list[str] | None,
) -> list[str]:
    if roles is not None:
        return list(roles)
    if user_id is None:
        return []
    user = load_user_with_roles(session, user_id)
    return role_codes(user) if user else []


def resolve_customer_access_scope(
    session: Session,
    user_id: int | None,
    roles: list[str] | None = None,
) -> CustomerAccessScope:
    """按角色解析客户数据可见范围（取最宽权限）。"""
    if user_id is None:
        return CustomerAccessScope(mode="all")

    effective_roles = resolve_roles(session, user_id, roles)

    if Role.ADMIN in effective_roles:
        return CustomerAccessScope(mode="all")

    if Role.SALES_MANAGER in effective_roles:
        team_ids = get_team_user_ids(session, user_id)
        return CustomerAccessScope(mode="team", team_user_ids=tuple(team_ids))

    return CustomerAccessScope(mode="owner", owner_user_id=user_id)


def get_team_user_ids(session: Session, user_id: int) -> list[int]:
    """销售经理：同部门所有职员（含自身）对应的 user_id。"""
    employee = (
        session.query(Employee).filter(Employee.user_id == user_id).first()
    )
    if employee is None or not employee.department:
        return [user_id]

    rows = (
        session.query(Employee.user_id)
        .filter(
            Employee.department == employee.department,
            Employee.user_id.isnot(None),
        )
        .all()
    )
    team_ids = sorted({row[0] for row in rows if row[0] is not None})
    return team_ids or [user_id]


def assert_customer_access(
    session: Session,
    customer: Customer,
    user_id: int | None,
    roles: list[str] | None = None,
) -> None:
    """校验当前用户是否可访问指定客户。"""
    if user_id is None:
        return

    scope = resolve_customer_access_scope(session, user_id, roles)
    if scope.mode == "all":
        return

    owner_id = customer.owner_user_id
    if scope.mode == "owner":
        if owner_id != user_id:
            raise PermissionDeniedError("无权访问该客户")
        return

    if owner_id not in scope.team_user_ids:
        raise PermissionDeniedError("无权访问该客户")


def can_view_employee_customers(
    session: Session,
    *,
    viewer_user_id: int,
    target_employee_user_id: int | None,
    roles: list[str] | None = None,
) -> bool:
    """是否允许查看某职员对接的客户名单。"""
    if target_employee_user_id is None:
        return False

    effective_roles = resolve_roles(session, viewer_user_id, roles)
    if Role.ADMIN in effective_roles:
        return True

    if target_employee_user_id == viewer_user_id:
        return True

    if Role.SALES_MANAGER in effective_roles:
        team_ids = get_team_user_ids(session, viewer_user_id)
        return target_employee_user_id in team_ids

    return False
