from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SessionInfo(BaseModel):
    session_id: str
    user_id: int
    title: str = "新会话"
    created_at: datetime | None = None
    last_active: datetime | None = None


class SessionCreateRequest(BaseModel):
    title: str = Field(default="新会话", max_length=255)


class SessionCreateResponse(BaseModel):
    session: SessionInfo


class SessionListResponse(BaseModel):
    sessions: list[SessionInfo]
    total: int


class SessionDeleteResponse(BaseModel):
    session_id: str
    deleted: bool = True
    memory: dict[str, int] = Field(default_factory=dict)
