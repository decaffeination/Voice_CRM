"""Chat memory ORM repository (messages, state, summary)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from main_server.DB.models import ChatMessageORM, ChatStateORM, ChatSummaryORM


def list_messages(session: Session, session_id: str) -> list[ChatMessageORM]:
    return (
        session.query(ChatMessageORM)
        .filter(ChatMessageORM.session_id == session_id)
        .order_by(ChatMessageORM.id.asc())
        .all()
    )


def list_messages_desc(
    session: Session,
    session_id: str,
    *,
    limit: int,
) -> list[ChatMessageORM]:
    return (
        session.query(ChatMessageORM)
        .filter(ChatMessageORM.session_id == session_id)
        .order_by(ChatMessageORM.id.desc())
        .limit(limit)
        .all()
    )


def count_messages(session: Session, session_id: str) -> int:
    return (
        session.query(ChatMessageORM)
        .filter(ChatMessageORM.session_id == session_id)
        .count()
    )


def append_messages(
    session: Session,
    session_id: str,
    messages: list[dict],
) -> None:
    for item in messages:
        session.add(
            ChatMessageORM(
                session_id=session_id,
                role=item["role"],
                content=item["content"],
                channel=item.get("channel", "text"),
            )
        )


def list_messages_asc_limit(
    session: Session,
    session_id: str,
    *,
    limit: int,
) -> list[ChatMessageORM]:
    return (
        session.query(ChatMessageORM)
        .filter(ChatMessageORM.session_id == session_id)
        .order_by(ChatMessageORM.id.asc())
        .limit(limit)
        .all()
    )


def delete_message_rows(session: Session, rows: list[ChatMessageORM]) -> int:
    for row in rows:
        session.delete(row)
    return len(rows)


def get_state_row(session: Session, session_id: str) -> ChatStateORM | None:
    return (
        session.query(ChatStateORM)
        .filter(ChatStateORM.session_id == session_id)
        .first()
    )


def upsert_state_row(
    session: Session,
    session_id: str,
    state_json: str,
) -> None:
    row = get_state_row(session, session_id)
    if row is None:
        session.add(ChatStateORM(session_id=session_id, state_json=state_json))
    else:
        row.state_json = state_json


def delete_state_row(session: Session, session_id: str) -> int:
    row = get_state_row(session, session_id)
    if row is None:
        return 0
    session.delete(row)
    return 1


def get_summary_row(session: Session, session_id: str) -> ChatSummaryORM | None:
    return (
        session.query(ChatSummaryORM)
        .filter(ChatSummaryORM.session_id == session_id)
        .first()
    )


def upsert_summary_row(
    session: Session,
    session_id: str,
    summary_text: str,
) -> None:
    row = get_summary_row(session, session_id)
    if row is None:
        session.add(
            ChatSummaryORM(session_id=session_id, summary_text=summary_text)
        )
    else:
        row.summary_text = summary_text


def delete_summary_row(session: Session, session_id: str) -> int:
    row = get_summary_row(session, session_id)
    if row is None:
        return 0
    session.delete(row)
    return 1
