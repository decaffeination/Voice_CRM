from __future__ import annotations

from main_server.DB import db_session
from main_server.DB.models import ChatMessageORM
from main_server.DB.repositories import memory_repo
from main_server.config.settings import get_settings
from main_server.memory.memory_schema import HistoryMessage


def _to_message(row: ChatMessageORM) -> HistoryMessage:
    return HistoryMessage(
        id=row.id,
        role=row.role,
        content=row.content,
        channel=row.channel or "text",
        created_at=row.created_at,
    )


def load_all(session_id: str) -> list[HistoryMessage]:
    with db_session() as session:
        rows = memory_repo.list_messages(session, session_id)
        return [_to_message(row) for row in rows]


def load_active(session_id: str) -> list[HistoryMessage]:
    settings = get_settings()
    round_limit = settings.memory.history_active_rounds
    message_limit = max(round_limit * 2, 1)
    with db_session() as session:
        rows = memory_repo.list_messages_desc(
            session, session_id, limit=message_limit
        )
        rows.reverse()
        return [_to_message(row) for row in rows]


def count(session_id: str) -> int:
    with db_session() as session:
        return memory_repo.count_messages(session, session_id)


def append(session_id: str, messages: list[dict]) -> None:
    if not messages:
        return
    with db_session() as session:
        memory_repo.append_messages(session, session_id, messages)


def load_older_than(session_id: str, keep_last: int) -> list[HistoryMessage]:
    with db_session() as session:
        total = memory_repo.count_messages(session, session_id)
        if total <= keep_last:
            return []
        offset = total - keep_last
        rows = memory_repo.list_messages_asc_limit(
            session, session_id, limit=offset
        )
        return [_to_message(row) for row in rows]


def delete_older_than(session_id: str, keep_last: int) -> int:
    with db_session() as session:
        rows = memory_repo.list_messages(session, session_id)
        if len(rows) <= keep_last:
            return 0
        to_delete = rows[: len(rows) - keep_last]
        return memory_repo.delete_message_rows(session, to_delete)


def delete_all(session_id: str) -> int:
    with db_session() as session:
        rows = memory_repo.list_messages(session, session_id)
        return memory_repo.delete_message_rows(session, rows)
