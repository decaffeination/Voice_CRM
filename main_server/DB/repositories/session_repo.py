"""Chat session ORM repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from main_server.DB.models import ChatSessionORM


def create_row(
    session: Session,
    *,
    session_id: str,
    user_id: int,
    title: str,
) -> ChatSessionORM:
    row = ChatSessionORM(session_id=session_id, user_id=user_id, title=title)
    session.add(row)
    session.flush()
    session.refresh(row)
    return row


def get_by_id(session: Session, session_id: str) -> ChatSessionORM | None:
    return (
        session.query(ChatSessionORM)
        .filter(ChatSessionORM.session_id == session_id)
        .first()
    )


def list_by_user_id(session: Session, user_id: int) -> list[ChatSessionORM]:
    return (
        session.query(ChatSessionORM)
        .filter(ChatSessionORM.user_id == user_id)
        .order_by(ChatSessionORM.last_active.desc())
        .all()
    )


def touch(session: Session, row: ChatSessionORM) -> ChatSessionORM:
    row.last_active = datetime.now()
    session.flush()
    session.refresh(row)
    return row


def update_title(session: Session, row: ChatSessionORM, title: str) -> ChatSessionORM:
    row.title = title
    session.flush()
    session.refresh(row)
    return row


def delete_row(session: Session, row: ChatSessionORM) -> None:
    session.delete(row)
