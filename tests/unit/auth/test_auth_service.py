"""认证服务单元测试。"""

from __future__ import annotations

import pytest

from main_server.core.auth.auth_service import (
    authenticate,
    hash_password,
    login,
    verify_password,
)
from main_server.core.auth.permission import Role
from main_server.core.auth.user_service import create_user
from main_server.core.exceptions import AuthError, ValidationError
from main_server.DB import db_session


class TestPasswordUtils:
    def test_hash_and_verify(self) -> None:
        # 场景：密码哈希校验；输入：明文密码；预期：verify 通过
        hashed = hash_password("secret12")
        assert verify_password("secret12", hashed)
        assert not verify_password("wrong", hashed)


class TestAuthenticate:
    def test_wrong_password(self, memory_db) -> None:
        # 场景：密码错误；输入：错误密码；预期：AuthError
        with db_session() as session:
            create_user(
                session,
                username="auth_user",
                password="pass1234",
                roles=[Role.SALES],
            )
            with pytest.raises(AuthError, match="用户名或密码"):
                authenticate(session, "auth_user", "wrongpass")

    def test_login_returns_token(self, memory_db) -> None:
        # 场景：登录成功；输入：正确凭据；预期：access_token 非空
        with db_session() as session:
            create_user(
                session,
                username="login_user",
                password="login123",
                roles=[Role.SALES],
            )
            token_resp = login(session, "login_user", "login123")
        assert token_resp.access_token

    def test_duplicate_username_on_create(self, memory_db) -> None:
        # 场景：重复用户名；输入：已存在 username；预期：ValidationError
        with db_session() as session:
            create_user(session, username="dup", password="dup1234", roles=[Role.SALES])
            with pytest.raises(ValidationError, match="已存在"):
                create_user(session, username="dup", password="dup1234", roles=[Role.SALES])
