from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from main_server.DB.base import Base


class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(64), nullable=False, index=True)
    resource = Column(String(255), default="")
    detail = Column(Text, default="")
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    session_id = Column(String(64))
    request_id = Column(String(32))
    created_at = Column(DateTime, server_default=func.now(), index=True)
