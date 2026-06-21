from __future__ import annotations

from fastapi import APIRouter, Depends

from main_server.api.deps.auth_dep import CurrentUser, require_business_user
from main_server.core.logger import logger
from main_server.memory.memory_manager import memory_manager
from main_server.memory.memory_schema import SessionMessagesResponse
from main_server.session.session_manager import session_manager

router = APIRouter(prefix="/api", tags=["memory"])


@router.get("/session/{session_id}/messages", response_model=SessionMessagesResponse)
def get_session_messages(
    session_id: str,
    current_user: CurrentUser = Depends(require_business_user),
):
    session_manager.get(session_id, current_user.user_id)
    messages = memory_manager.load_history_all(session_id)
    summary = memory_manager.load_summary(session_id)
    logger.info(
        "api.memory.messages session_id=%s total=%s has_summary=%s",
        session_id,
        len(messages),
        bool(summary),
    )
    return SessionMessagesResponse(
        session_id=session_id,
        messages=messages,
        total=len(messages),
        summary=summary,
    )
