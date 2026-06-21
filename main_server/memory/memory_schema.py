from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from agent.state import ConversationState, default_conversation_state

if TYPE_CHECKING:
    from main_server.core.auth.auth_schema import CurrentUser


class HistoryMessage(BaseModel):
    id: int | None = None
    role: str
    content: str
    channel: str = "text"
    created_at: datetime | None = None


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: list[HistoryMessage] = Field(default_factory=list)
    total: int = 0
    summary: str | None = None


class MemorySnapshot(BaseModel):
    session_id: str
    history: list[HistoryMessage] = Field(default_factory=list)
    state: ConversationState = Field(default_factory=default_conversation_state)
    summary: str | None = None
    user_id: int | None = None


class ActorContext(BaseModel):
    """每轮对话的运行时操作者上下文（不持久化到 Memory）。"""

    user_id: int
    username: str
    roles: list[str] = Field(default_factory=list)
    display_name: str | None = None
    session_id: str
    channel: str = "text"

    @classmethod
    def from_current_user(
        cls,
        user: CurrentUser,
        *,
        session_id: str,
        channel: str = "text",
    ) -> ActorContext:
        return cls(
            user_id=user.user_id,
            username=user.username,
            roles=list(user.roles),
            display_name=user.display_name,
            session_id=session_id,
            channel=channel,
        )


class TurnContext(BaseModel):
    """Pipeline 单轮入口：操作者 + 用户输入（Memory 由 Graph memory_load 加载）。"""

    actor: ActorContext
    user_input: str

    @property
    def session_id(self) -> str:
        return self.actor.session_id
