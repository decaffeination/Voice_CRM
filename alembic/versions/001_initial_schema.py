"""Initial schema from ORM metadata."""

from __future__ import annotations

import main_server.DB.models  # noqa: F401
from alembic import op
from main_server.DB.base import Base

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
