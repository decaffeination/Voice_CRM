"""Audit logging: logger output and database persistence."""

from __future__ import annotations

from typing import Any

from main_server.core.context import get_request_id, session_id_var, user_id_var
from main_server.core.logger import logger
from main_server.DB import db_session
from main_server.DB.repositories import audit_repo


def audit_log(
    action: str,
    *,
    resource: str = "",
    detail: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    """Audit log; request_id/user_id/session_id from contextvars."""
    user_id = user_id_var.get()
    session_id = session_id_var.get()
    request_id = get_request_id()

    parts = [f"audit action={action}"]
    if resource:
        parts.append(f"resource={resource}")
    if detail:
        parts.append(f"detail={detail}")
    if user_id is not None:
        parts.append(f"user_id={user_id}")
    if session_id:
        parts.append(f"session_id={session_id}")
    if request_id and request_id != "-":
        parts.append(f"request_id={request_id}")
    if extra:
        for key, value in extra.items():
            parts.append(f"{key}={value}")
    logger.info(" ".join(parts))

    detail_text = detail
    if extra:
        extra_text = " ".join(f"{k}={v}" for k, v in extra.items())
        detail_text = f"{detail_text} {extra_text}".strip()

    try:
        with db_session() as session:
            audit_repo.insert(
                session,
                action=action,
                resource=resource or "",
                detail=detail_text or "",
                user_id=user_id,
                session_id=session_id,
                request_id=request_id if request_id != "-" else None,
            )
    except Exception:
        logger.exception("audit.persist_failed action=%s", action)
