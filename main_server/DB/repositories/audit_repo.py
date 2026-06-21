"""Audit log ORM repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from main_server.DB.models.audit_log import AuditLogORM
from main_server.DB.search import case_insensitive_like


def insert(
    session: Session,
    *,
    action: str,
    resource: str,
    detail: str,
    user_id: int | None,
    session_id: str | None,
    request_id: str | None,
) -> AuditLogORM:
    row = AuditLogORM(
        action=action,
        resource=resource,
        detail=detail,
        user_id=user_id,
        session_id=session_id,
        request_id=request_id,
    )
    session.add(row)
    return row


def list_logs(
    session: Session,
    *,
    user_id: int | None,
    action: str | None,
    limit: int,
    offset: int,
    dialect: str,
) -> tuple[list[AuditLogORM], int]:
    query = session.query(AuditLogORM)
    if user_id is not None:
        query = query.filter(AuditLogORM.user_id == user_id)
    if action:
        keyword = action.strip()
        if keyword:
            query = query.filter(
                case_insensitive_like(AuditLogORM.action, f"%{keyword}%", dialect)
            )

    total = query.count()
    rows = (
        query.order_by(AuditLogORM.id.desc())
        .offset(max(offset, 0))
        .limit(min(max(limit, 1), 200))
        .all()
    )
    return rows, total


def to_dict(record: AuditLogORM) -> dict[str, Any]:
    return {
        "id": record.id,
        "action": record.action,
        "resource": record.resource or "",
        "detail": record.detail or "",
        "user_id": record.user_id,
        "session_id": record.session_id,
        "request_id": record.request_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
