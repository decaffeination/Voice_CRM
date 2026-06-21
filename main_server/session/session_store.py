from __future__ import annotations

from main_server.DB import db_session
from main_server.DB.repositories import session_repo
from main_server.session.session_schema import SessionInfo


def _to_info(row) -> SessionInfo:
    return SessionInfo(
        session_id=row.session_id,
        user_id=row.user_id,
        title=row.title,
        created_at=row.created_at,
        last_active=row.last_active,
    )


def create(session_id: str, user_id: int, title: str = "新会话") -> SessionInfo:
    with db_session() as session:
        row = session_repo.create_row(
            session,
            session_id=session_id,
            user_id=user_id,
            title=title,
        )
        return _to_info(row)


def get(session_id: str) -> SessionInfo | None:
    with db_session() as session:
        row = session_repo.get_by_id(session, session_id)
        return _to_info(row) if row else None


def list_by_user(user_id: int) -> list[SessionInfo]:
    with db_session() as session:
        rows = session_repo.list_by_user_id(session, user_id)
        return [_to_info(row) for row in rows]


def touch(session_id: str) -> SessionInfo | None:
    with db_session() as session:
        row = session_repo.get_by_id(session, session_id)
        if row is None:
            return None
        row = session_repo.touch(session, row)
        return _to_info(row)


def update_title(session_id: str, title: str) -> SessionInfo | None:
    with db_session() as session:
        row = session_repo.get_by_id(session, session_id)
        if row is None:
            return None
        row = session_repo.update_title(session, row, title)
        return _to_info(row)


def delete(session_id: str) -> bool:
    with db_session() as session:
        row = session_repo.get_by_id(session, session_id)
        if row is None:
            return False
        session_repo.delete_row(session, row)
        return True
