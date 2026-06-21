from __future__ import annotations

import json

from agent.state import ConversationState, default_conversation_state
from main_server.DB import db_session
from main_server.DB.repositories import memory_repo


def load(session_id: str) -> ConversationState:
    with db_session() as session:
        row = memory_repo.get_state_row(session, session_id)
        if row is None:
            return default_conversation_state()
        data = json.loads(row.state_json or "{}")
        merged = default_conversation_state()
        merged.update(data)
        if "customer_context" in data:
            merged["customer_context"] = {
                **default_conversation_state()["customer_context"],
                **data["customer_context"],
            }
        return merged


def save(session_id: str, state: ConversationState) -> None:
    payload = json.dumps(state, ensure_ascii=False, default=str)
    with db_session() as session:
        memory_repo.upsert_state_row(session, session_id, payload)


def delete(session_id: str) -> int:
    with db_session() as session:
        return memory_repo.delete_state_row(session, session_id)
