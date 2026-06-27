"""Knowledge document registry: doc_id, content hash, version, ingest status."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from main_server.DB import db_session
from main_server.DB.models.knowledge_document import KnowledgeDocumentORM
from main_server.DB.repositories import knowledge_repo


@dataclass
class KnowledgeDocumentRecord:
    doc_id: str
    filename: str
    file_hash: str
    version: int
    chunk_count: int
    file_path: str
    status: str
    operator_user_id: int | None
    ingested_at: Any
    updated_at: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "file_hash": self.file_hash,
            "version": self.version,
            "chunk_count": self.chunk_count,
            "file_path": self.file_path,
            "status": self.status,
            "operator_user_id": self.operator_user_id,
            "ingested_at": self.ingested_at.isoformat() if self.ingested_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def build_doc_id(filename: str) -> str:
    normalized = filename.strip().replace("\\", "/").lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def compute_file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_document(doc_id: str) -> KnowledgeDocumentRecord | None:
    with db_session() as session:
        row = knowledge_repo.get_by_doc_id(session, doc_id)
        if row is None:
            return None
        return _to_record(row)


def list_documents(*, include_deleted: bool = False) -> list[KnowledgeDocumentRecord]:
    with db_session() as session:
        rows = knowledge_repo.list_all(session, include_deleted=include_deleted)
        return [_to_record(row) for row in rows]


def upsert_active_document(
    *,
    doc_id: str,
    filename: str,
    file_hash: str,
    chunk_count: int,
    file_path: str,
    operator_user_id: int | None,
    version: int,
) -> KnowledgeDocumentRecord:
    with db_session() as session:
        row = knowledge_repo.upsert_active(
            session,
            doc_id=doc_id,
            filename=filename,
            file_hash=file_hash,
            chunk_count=chunk_count,
            file_path=file_path,
            operator_user_id=operator_user_id,
            version=version,
        )
        return _to_record(row)


def mark_document_deleted(doc_id: str) -> KnowledgeDocumentRecord | None:
    with db_session() as session:
        row = knowledge_repo.mark_deleted(session, doc_id)
        if row is None:
            return None
        return _to_record(row)


def _to_record(row: KnowledgeDocumentORM) -> KnowledgeDocumentRecord:
    return KnowledgeDocumentRecord(
        doc_id=row.doc_id,
        filename=row.filename,
        file_hash=row.file_hash,
        version=row.version,
        chunk_count=row.chunk_count,
        file_path=row.file_path or "",
        status=row.status,
        operator_user_id=row.operator_user_id,
        ingested_at=row.ingested_at,
        updated_at=row.updated_at,
    )
