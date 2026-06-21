from __future__ import annotations

from main_server.DB import db_session
from main_server.DB.repositories import memory_repo


def load(session_id: str) -> str | None:
    with db_session() as session:
        row = memory_repo.get_summary_row(session, session_id)
        if row is None or not row.summary_text:
            return None
        return row.summary_text


def save(session_id: str, summary: str) -> None:
    with db_session() as session:
        memory_repo.upsert_summary_row(session, session_id, summary)


def delete(session_id: str) -> int:
    with db_session() as session:
        return memory_repo.delete_summary_row(session, session_id)
