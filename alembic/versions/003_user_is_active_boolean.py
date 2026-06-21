"""users.is_active: Integer -> Boolean."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def _is_active_already_boolean(bind) -> bool:
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return True
    for col in inspector.get_columns("users"):
        if col["name"] != "is_active":
            continue
        return isinstance(col["type"], sa.Boolean)
    return True


def upgrade() -> None:
    bind = op.get_bind()
    if _is_active_already_boolean(bind):
        return

    dialect = bind.dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "is_active",
                existing_type=sa.Integer(),
                type_=sa.Boolean(),
                existing_nullable=False,
                nullable=False,
            )
    else:
        op.alter_column(
            "users",
            "is_active",
            existing_type=sa.Integer(),
            type_=sa.Boolean(),
            existing_nullable=False,
            nullable=False,
            postgresql_using="(is_active <> 0)",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if not _is_active_already_boolean(bind):
        return

    dialect = bind.dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "is_active",
                existing_type=sa.Boolean(),
                type_=sa.Integer(),
                existing_nullable=False,
                nullable=False,
            )
    else:
        op.alter_column(
            "users",
            "is_active",
            existing_type=sa.Boolean(),
            type_=sa.Integer(),
            existing_nullable=False,
            nullable=False,
            postgresql_using="CASE WHEN is_active THEN 1 ELSE 0 END",
        )
