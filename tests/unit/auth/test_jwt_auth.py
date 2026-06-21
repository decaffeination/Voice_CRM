"""JWT 认证单元测试。"""

from __future__ import annotations

import pytest

from main_server.core.auth.jwt_auth import (
    create_access_token,
    decode_access_token,
    get_current_user_from_token,
)
from main_server.core.auth.permission import Role
from main_server.core.exceptions import AuthError


class TestJWT:
    def test_token_contains_roles(self) -> None:
        # 场景：签发含角色 token；输入：admin 角色；预期：payload 正确
        token = create_access_token(
            user_id=1,
            username="admin",
            roles=[Role.ADMIN],
            display_name="管理员",
        )
        payload = decode_access_token(token)
        assert payload.user_id == 1
        assert payload.username == "admin"
        assert payload.roles == [Role.ADMIN]
        assert payload.display_name == "管理员"

    def test_invalid_token_raises_auth_error(self) -> None:
        # 场景：无效 token；输入：伪造字符串；预期：AuthError
        with pytest.raises(AuthError, match="无效"):
            decode_access_token("invalid.token.here")

    def test_expired_token_raises_auth_error(self, monkeypatch) -> None:
        # 场景：过期 token；输入：负 expire；预期：AuthError
        from datetime import datetime, timedelta, timezone

        import jwt

        from main_server.config.settings import get_settings

        settings = get_settings()
        expire = datetime.now(timezone.utc) - timedelta(minutes=1)
        payload = {
            "sub": "1",
            "user_id": 1,
            "username": "admin",
            "roles": [],
            "exp": expire,
        }
        token = jwt.encode(
            payload, settings.jwt.secret_key, algorithm=settings.jwt.algorithm
        )
        with pytest.raises(AuthError):
            decode_access_token(token)

    def test_get_current_user_from_token(self) -> None:
        # 场景：token 转 CurrentUser；输入：有效 token；预期：user_id/roles 正确
        token = create_access_token(42, "user42", [Role.SALES])
        user = get_current_user_from_token(token)
        assert user.user_id == 42
        assert user.username == "user42"
        assert Role.SALES in user.roles
