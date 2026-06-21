"""角色定义与权限校验。"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from main_server.core.auth.auth_schema import CurrentUser
from main_server.core.auth.jwt_auth import get_current_user
from main_server.core.exceptions import PermissionDeniedError
from main_server.DB.models import User


class Role:
    ADMIN = "Admin"
    SALES_MANAGER = "SalesManager"
    SALES = "Sales"
    CUSTOMER_SERVICE = "CustomerService"

    ALL: frozenset[str] = frozenset(
        {ADMIN, SALES_MANAGER, SALES, CUSTOMER_SERVICE}
    )


DEFAULT_ROLE_SEEDS: tuple[tuple[str, str, str], ...] = (
    (Role.ADMIN, "管理员", "系统管理员，拥有全部权限"),
    (Role.SALES_MANAGER, "销售经理", "销售团队管理，可查看团队客户"),
    (Role.SALES, "销售", "一线销售，管理自己的客户"),
    (Role.CUSTOMER_SERVICE, "客服", "客户服务，处理咨询与跟进"),
)


def normalize_roles(roles: list[str] | None) -> list[str]:
    """校验并去重角色代码，非法角色抛出 ValueError。"""
    if not roles:
        raise ValueError("至少指定一个角色")
    normalized: list[str] = []
    seen: set[str] = set()
    for role in roles:
        code = role.strip()
        if code not in Role.ALL:
            raise ValueError(f"无效角色: {role}")
        if code not in seen:
            seen.add(code)
            normalized.append(code)
    return normalized


def role_codes(user: User) -> list[str]:
    return [role.code for role in user.roles]


def user_has_any_role(user: User | CurrentUser, *allowed: str) -> bool:
    codes = user.roles if isinstance(user, CurrentUser) else role_codes(user)
    allowed_set = set(allowed)
    return any(code in allowed_set for code in codes)


def user_is_admin(user: User | CurrentUser) -> bool:
    return user_has_any_role(user, Role.ADMIN)


def load_user_with_roles(session: Session, user_id: int) -> User | None:
    return (
        session.query(User)
        .options(joinedload(User.roles))
        .filter(User.id == user_id)
        .first()
    )


def user_is_admin_by_id(session: Session, user_id: int) -> bool:
    user = load_user_with_roles(session, user_id)
    return user is not None and user_is_admin(user)


def require_roles(*allowed: str) -> Callable[..., CurrentUser]:
    """FastAPI 依赖：要求当前用户至少拥有一个指定角色。"""

    async def _checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not user_has_any_role(current_user, *allowed):
            raise PermissionDeniedError("无权访问该资源")
        return current_user

    return _checker


require_admin = require_roles(Role.ADMIN)

# 可访问 CRM / 对话 / 语音等业务能力的角色
BUSINESS_ROLES: frozenset[str] = frozenset(
    {Role.ADMIN, Role.SALES_MANAGER, Role.SALES, Role.CUSTOMER_SERVICE}
)

require_crm_read = require_roles(
    Role.ADMIN,
    Role.SALES_MANAGER,
    Role.SALES,
    Role.CUSTOMER_SERVICE,
)
require_business_user = require_crm_read


def user_has_business_role(user: User | CurrentUser) -> bool:
    return user_has_any_role(user, *BUSINESS_ROLES)
