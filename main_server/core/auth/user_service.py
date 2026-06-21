"""用户管理业务逻辑。"""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from main_server.core.auth.auth_service import hash_password, verify_password
from main_server.core.auth.permission import Role as RoleCode, normalize_roles, role_codes
from main_server.core.exceptions import (
    AuthError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from main_server.config.settings import get_settings
from main_server.DB.models import Role as RoleModel, User
from main_server.DB.repositories import user_repo
from main_server.DB.search import case_insensitive_like


def _get_user_by_id(session: Session, user_id: int) -> User | None:
    return user_repo.get_by_id(session, user_id)


def _resolve_roles(session: Session, role_codes_list: list[str]) -> list[RoleModel]:
    codes = normalize_roles(role_codes_list)
    roles = user_repo.get_roles_by_codes(session, codes)
    found = {role.code for role in roles}
    missing = [code for code in codes if code not in found]
    if missing:
        raise ValidationError(f"角色不存在: {', '.join(missing)}")
    return roles


def _count_admin_users(session: Session) -> int:
    return user_repo.count_admin_users(session)


def _assert_can_remove_admin(session: Session, user: User, new_roles: list[str]) -> None:
    if RoleCode.ADMIN not in role_codes(user):
        return
    if RoleCode.ADMIN in normalize_roles(new_roles):
        return
    if _count_admin_users(session) <= 1:
        raise PermissionDeniedError("不能移除最后一个管理员的角色")


def _purge_user_dependents(session: Session, user_id: int) -> None:
    user_repo.purge_user_dependents(session, user_id)


def create_user(
    session: Session,
    *,
    username: str,
    password: str,
    display_name: str | None = None,
    roles: list[str],
) -> User:
    username = username.strip()
    if not username:
        raise ValidationError("用户名不能为空")
    if len(password) < 6:
        raise ValidationError("密码长度不能少于 6 位")
    if user_repo.get_by_username_exists(session, username):
        raise ValidationError(f"用户名已存在: {username}")

    user = User(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name or username,
        is_active=True,
    )
    user.roles = _resolve_roles(session, roles)
    session.add(user)
    session.flush()
    session.refresh(user)
    return user


def list_users(
    session: Session,
    *,
    keyword: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[User], int]:
    query = session.query(User).options(joinedload(User.roles))
    dialect = get_settings().database.dialect
    if keyword and keyword.strip():
        like = f"%{keyword.strip()}%"
        query = query.filter(
            case_insensitive_like(User.username, like, dialect)
            | case_insensitive_like(User.display_name, like, dialect)
        )
    if role and role.strip():
        code = role.strip()
        if code not in RoleCode.ALL:
            raise ValidationError(f"无效角色: {role}")
        query = query.join(User.roles).filter(RoleModel.code == code).distinct()
    if is_active is not None:
        query = query.filter(User.is_active.is_(is_active))
    total = query.count()
    users = (
        query.order_by(User.id.desc()).offset(offset).limit(limit).all()
    )
    return users, total


def update_user(
    session: Session,
    user_id: int,
    *,
    display_name: str | None = None,
    is_active: bool | None = None,
) -> User:
    user = _get_user_by_id(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    if display_name is not None:
        name = display_name.strip()
        user.display_name = name or user.username
    if is_active is not None:
        user.is_active = is_active
    session.flush()
    session.refresh(user)
    return user


def update_user_roles(
    session: Session,
    user_id: int,
    roles: list[str],
    *,
    operator_user_id: int | None = None,
) -> User:
    user = _get_user_by_id(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    _assert_can_remove_admin(session, user, roles)
    user.roles = _resolve_roles(session, roles)
    session.flush()
    session.refresh(user)
    return user


def delete_user(
    session: Session,
    user_id: int,
    *,
    operator_user_id: int,
) -> None:
    if user_id == operator_user_id:
        raise PermissionDeniedError("不能删除当前登录账号")
    user = _get_user_by_id(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    if RoleCode.ADMIN in role_codes(user) and _count_admin_users(session) <= 1:
        raise PermissionDeniedError("不能删除最后一个管理员")
    _purge_user_dependents(session, user_id)
    session.delete(user)
    session.flush()


def change_password(
    session: Session,
    user_id: int,
    *,
    old_password: str,
    new_password: str,
) -> None:
    if len(new_password) < 6:
        raise ValidationError("新密码长度不能少于 6 位")
    user = _get_user_by_id(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    if not verify_password(old_password, user.password_hash):
        raise AuthError("原密码错误")
    user.password_hash = hash_password(new_password)


def reset_password(session: Session, user_id: int, new_password: str) -> None:
    if len(new_password) < 6:
        raise ValidationError("新密码长度不能少于 6 位")
    user = _get_user_by_id(session, user_id)
    if user is None:
        raise NotFoundError("用户不存在")
    user.password_hash = hash_password(new_password)


def user_to_dict(user: User) -> dict:
    return {
        "user_id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "roles": role_codes(user),
        "is_active": bool(user.is_active),
    }
