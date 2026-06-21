from __future__ import annotations

from fastapi import APIRouter, Depends

from main_server.api.deps.auth_dep import CurrentUser, require_business_user
from main_server.session.session_manager import session_manager
from main_server.session.session_schema import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDeleteResponse,
    SessionInfo,
    SessionListResponse,
)

router = APIRouter(prefix="/api", tags=["session"])


@router.post("/session", response_model=SessionCreateResponse)
def create_session(
    body: SessionCreateRequest,
    current_user: CurrentUser = Depends(require_business_user),
):
    session = session_manager.create(current_user.user_id, title=body.title)
    return SessionCreateResponse(session=session)


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(current_user: CurrentUser = Depends(require_business_user)):
    sessions = session_manager.list_by_user(current_user.user_id)
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.get("/session/{session_id}", response_model=SessionInfo)
def get_session(
    session_id: str,
    current_user: CurrentUser = Depends(require_business_user),
):
    return session_manager.get(session_id, current_user.user_id)


@router.delete("/session/{session_id}", response_model=SessionDeleteResponse)
def delete_session(
    session_id: str,
    current_user: CurrentUser = Depends(require_business_user),
):
    memory_deleted = session_manager.delete(session_id, current_user.user_id)
    return SessionDeleteResponse(session_id=session_id, memory=memory_deleted)
