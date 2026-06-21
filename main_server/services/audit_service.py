from __future__ import annotations

from typing import Any

from main_server.config.settings import get_settings
from main_server.DB import db_session
from main_server.DB.repositories import audit_repo


def to_dict(record) -> dict[str, Any]:
    return audit_repo.to_dict(record)


def list_audit_logs(
    *,
    user_id: int | None = None,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    dialect = get_settings().database.dialect
    with db_session() as session:
        rows, total = audit_repo.list_logs(
            session,
            user_id=user_id,
            action=action,
            limit=limit,
            offset=offset,
            dialect=dialect,
        )
        return [audit_repo.to_dict(row) for row in rows], total
