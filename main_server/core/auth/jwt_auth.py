from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from main_server.config.settings import get_settings
from main_server.core.auth.auth_schema import CurrentUser, TokenPayload
from main_server.core.exceptions import AuthError

security = HTTPBearer(auto_error=False)


def create_access_token(
    user_id: int,
    username: str,
    roles: list[str] | None = None,
    *,
    display_name: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt.expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "user_id": user_id,
        "username": username,
        "roles": roles or [],
        "display_name": display_name,
        "exp": expire,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(
        payload,
        settings.jwt.secret_key,
        algorithm=settings.jwt.algorithm,
    )


def decode_access_token(token: str) -> TokenPayload:
    settings = get_settings()
    try:
        data = jwt.decode(
            token,
            settings.jwt.secret_key,
            algorithms=[settings.jwt.algorithm],
        )
        if "roles" not in data:
            data["roles"] = []
        return TokenPayload(**data)
    except jwt.PyJWTError as exc:
        raise AuthError("无效或过期的令牌") from exc


def get_current_user_from_token(token: str) -> CurrentUser:
    payload = decode_access_token(token)
    return CurrentUser(
        user_id=payload.user_id,
        username=payload.username,
        display_name=payload.display_name,
        roles=list(payload.roles),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUser:
    """FastAPI 依赖：JWT 校验并返回当前用户（含 roles）。"""
    if credentials is None or not credentials.credentials:
        raise AuthError("未提供认证令牌")
    return get_current_user_from_token(credentials.credentials)
