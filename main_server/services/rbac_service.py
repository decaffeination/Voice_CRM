"""RBAC 业务：权限目录种子、角色权限读写与校验。"""

from __future__ import annotations

from main_server.core.audit import audit_log
from main_server.core.auth.auth_schema import CurrentUser
from main_server.core.auth.permission import Role as RoleCode
from main_server.core.auth.rbac_catalog import (
    ADMIN_REQUIRED_PERMISSIONS,
    ALL_PERMISSION_CODES,
    DEFAULT_ROLE_PERMISSIONS,
    PERMISSION_TREE,
    PermissionNode,
    flatten_permission_tree,
)
from main_server.core.exceptions import NotFoundError, ValidationError
from main_server.DB import db_session
from main_server.DB.models import User
from main_server.DB.repositories import rbac_repo


def _node_to_dict(node: PermissionNode) -> dict:
    return {
        "key": node.key,
        "label": node.label,
        "children": [_node_to_dict(child) for child in node.children],
    }


def get_permission_tree() -> list[dict]:
    return [_node_to_dict(node) for node in PERMISSION_TREE]


def seed_permissions() -> None:
    with db_session() as session:
        for code, label, parent_code, sort_order in flatten_permission_tree():
            rbac_repo.upsert_permission(
                session,
                code=code,
                label=label,
                parent_code=parent_code,
                sort_order=sort_order,
            )


def seed_role_permissions() -> None:
    with db_session() as session:
        for role_code, codes in DEFAULT_ROLE_PERMISSIONS.items():
            role = rbac_repo.get_role_by_code(session, role_code)
            if role is None:
                continue
            if rbac_repo.role_has_any_permissions(session, role.id):
                continue
            rbac_repo.replace_role_permissions(session, role.id, codes)


def get_role_permissions(role_code: str) -> dict:
    with db_session() as session:
        role = rbac_repo.get_role_by_code(session, role_code)
        if role is None:
            raise NotFoundError(f"角色不存在: {role_code}")
        codes = rbac_repo.get_role_permission_codes(session, role.id)
        if not codes:
            codes = list(DEFAULT_ROLE_PERMISSIONS.get(role_code, []))
        return {"role_code": role_code, "permission_codes": sorted(codes)}


def update_role_permissions(
    role_code: str,
    permission_codes: list[str],
    *,
    operator_user_id: int | None = None,
) -> dict:
    normalized = _normalize_permission_codes(permission_codes)
    if role_code == RoleCode.ADMIN:
        missing = ADMIN_REQUIRED_PERMISSIONS - set(normalized)
        if missing:
            raise ValidationError(
                f"管理员角色必须保留权限: {', '.join(sorted(missing))}"
            )

    with db_session() as session:
        role = rbac_repo.get_role_by_code(session, role_code)
        if role is None:
            raise NotFoundError(f"角色不存在: {role_code}")
        before = rbac_repo.get_role_permission_codes(session, role.id)
        rbac_repo.replace_role_permissions(session, role.id, normalized)
        after = normalized

    audit_log(
        "settings.rbac_update",
        resource=f"role:{role_code}",
        detail=f"before={before} after={after}",
        extra={"operator_user_id": operator_user_id},
    )
    return {"role_code": role_code, "permission_codes": sorted(after)}


def _normalize_permission_codes(codes: list[str]) -> list[str]:
    if not codes:
        raise ValidationError("至少选择一个权限")
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in codes:
        code = raw.strip()
        if not code or code in seen:
            continue
        if code not in ALL_PERMISSION_CODES:
            raise ValidationError(f"无效权限: {code}")
        seen.add(code)
        normalized.append(code)
    if not normalized:
        raise ValidationError("至少选择一个有效权限")
    return normalized


def user_permission_codes(user: User | CurrentUser) -> set[str]:
    if isinstance(user, CurrentUser):
        role_codes = user.roles
    else:
        role_codes = [role.code for role in user.roles]

    merged: set[str] = set()
    with db_session() as session:
        for code in role_codes:
            role = rbac_repo.get_role_by_code(session, code)
            if role is None:
                continue
            stored = rbac_repo.get_role_permission_codes(session, role.id)
            if stored:
                merged.update(stored)
            else:
                merged.update(DEFAULT_ROLE_PERMISSIONS.get(code, []))
    return merged


def user_has_permission(user: User | CurrentUser, permission_code: str) -> bool:
    if user_is_admin(user):
        return True
    return permission_code in user_permission_codes(user)


def user_is_admin(user: User | CurrentUser) -> bool:
    if isinstance(user, CurrentUser):
        return RoleCode.ADMIN in user.roles
    return any(role.code == RoleCode.ADMIN for role in user.roles)
