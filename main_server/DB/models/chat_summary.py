from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func

from main_server.DB.base import Base


class ChatSummaryORM(Base):
    __tablename__ = "chat_summaries"

    session_id = Column(
        String(64),
        ForeignKey("chat_sessions.session_id"),
        primary_key=True,
    )
    summary_text = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
