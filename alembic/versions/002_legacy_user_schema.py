"""Legacy users table upgrades (RBAC columns + role migration).

Idempotent: safe on fresh installs and old SQLite databases.
"""

from __future__ import annotations

from sqlalchemy import inspect, text

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

_LEGACY_ROLE_MAP = {
    "admin": "Admin",
    "Admin": "Admin",
    "user": "Sales",
    "sales": "Sales",
    "Sales": "Sales",
}


def _table_columns(bind, table_name: str) -> set[str]:
    inspector = inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    columns = _table_columns(bind, "users")
    if not columns:
        return

    if "display_name" not in columns:
        op.add_column("users", sa.Column("display_name", sa.String(length=128)))
    if "is_active" not in columns:
        op.add_column(
            "users",
            sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        )
    if "updated_at" not in columns:
        op.add_column("users", sa.Column("updated_at", sa.DateTime()))

    columns = _table_columns(bind, "users")
    if "display_name" in columns:
        bind.execute(
            text(
                "UPDATE users SET display_name = username "
                "WHERE display_name IS NULL"
            )
        )
    if "updated_at" in columns:
        dialect = bind.dialect.name
        if dialect == "sqlite":
            bind.execute(
                text(
                    "UPDATE users SET updated_at = COALESCE("
                    "created_at, datetime('now')) "
                    "WHERE updated_at IS NULL"
                )
            )
        else:
            bind.execute(
                text(
                    "UPDATE users SET updated_at = COALESCE("
                    "created_at, CURRENT_TIMESTAMP) "
                    "WHERE updated_at IS NULL"
                )
            )

    columns = _table_columns(bind, "users")
    if "role" not in columns:
        return

    if _table_columns(bind, "roles") and _table_columns(bind, "user_roles"):
        role_rows = bind.execute(text("SELECT id, code FROM roles")).fetchall()
        role_by_code = {code: role_id for role_id, code in role_rows}
        user_rows = bind.execute(text("SELECT id, role FROM users")).fetchall()
        for user_id, legacy_role in user_rows:
            code = _LEGACY_ROLE_MAP.get(str(legacy_role), "Sales")
            role_id = role_by_code.get(code)
            if role_id is None:
                continue
            exists = bind.execute(
                text(
                    "SELECT 1 FROM user_roles "
                    "WHERE user_id = :user_id AND role_id = :role_id"
                ),
                {"user_id": user_id, "role_id": role_id},
            ).first()
            if exists is None:
                bind.execute(
                    text(
                        "INSERT INTO user_roles (user_id, role_id) "
                        "VALUES (:user_id, :role_id)"
                    ),
                    {"user_id": user_id, "role_id": role_id},
                )

    columns = _table_columns(bind, "users")
    if "role" not in columns:
        return

    dialect = bind.dialect.name
    if dialect == "sqlite":
        try:
            op.drop_column("users", "role")
            return
        except Exception:
            pass
        bind.execute(text("PRAGMA foreign_keys=OFF"))
        bind.execute(
            text(
                """
                CREATE TABLE users_new (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(64) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    display_name VARCHAR(128),
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        bind.execute(
            text(
                """
                INSERT INTO users_new (
                    id, username, password_hash, display_name,
                    is_active, created_at, updated_at
                )
                SELECT
                    id, username, password_hash,
                    COALESCE(display_name, username),
                    COALESCE(is_active, 1),
                    created_at, updated_at
                FROM users
                """
            )
        )
        bind.execute(text("DROP TABLE users"))
        bind.execute(text("ALTER TABLE users_new RENAME TO users"))
        bind.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username "
                "ON users (username)"
            )
        )
        bind.execute(text("PRAGMA foreign_keys=ON"))
    else:
        op.drop_column("users", "role")


def downgrade() -> None:
    # 数据迁移不可逆；保留空 downgrade。
    pass
