from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from main_server.DB.base import Base

DOC_STATUS_ACTIVE = "active"
DOC_STATUS_DELETED = "deleted"


class KnowledgeDocumentORM(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(String(64), unique=True, nullable=False, index=True)
    filename = Column(String(255), nullable=False, index=True)
    file_hash = Column(String(64), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    chunk_count = Column(Integer, nullable=False, default=0)
    file_path = Column(String(512), default="")
    status = Column(String(32), nullable=False, default=DOC_STATUS_ACTIVE, index=True)
    operator_user_id = Column(Integer, ForeignKey("users.id"), index=True)
    ingested_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )
