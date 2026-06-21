"""登录认证与密码工具。"""

from __future__ import annotations

import bcrypt
from sqlalchemy.orm import Session

from main_server.core.auth.auth_schema import TokenResponse
from main_server.core.auth.jwt_auth import create_access_token
from main_server.core.exceptions import AuthError
from main_server.DB.models import User
from main_server.DB.repositories import user_repo


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def _get_user_by_username(session: Session, username: str) -> User | None:
    return user_repo.get_by_username(session, username)


def authenticate(session: Session, username: str, password: str) -> User:
    user = _get_user_by_username(session, username.strip())
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("用户名或密码错误")
    if not user.is_active:
        raise AuthError("账号已停用")
    return user


def login(session: Session, username: str, password: str) -> TokenResponse:
    user = authenticate(session, username, password)
    roles = [role.code for role in user.roles]
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        roles=roles,
        display_name=user.display_name,
    )
    return TokenResponse(access_token=token)
