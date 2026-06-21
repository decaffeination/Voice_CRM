from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from main_server.DB.base import Base


class ChatSessionORM(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="新会话")
    created_at = Column(DateTime, server_default=func.now())
    last_active = Column(DateTime, server_default=func.now(), onupdate=func.now())
