"""PostgreSQL integration smoke test (requires running Postgres)."""

from __future__ import annotations

import pytest

from main_server.core.auth.permission import Role
from main_server.core.auth.user_service import create_user, list_users
from main_server.DB import db_session


@pytest.mark.postgres
def test_postgres_create_and_list_user(postgres_db) -> None:
    with db_session() as session:
        user = create_user(
            session,
            username="pg_user",
            password="pg123456",
            display_name="PG 用户",
            roles=[Role.SALES],
        )
        users, total = list_users(session, keyword="pg_user")
        assert total >= 1
        assert any(item.id == user.id for item in users)
