"""Knowledge document ORM repository."""

from __future__ import annotations

from sqlalchemy.orm import Session

from main_server.DB.models.knowledge_document import (
    DOC_STATUS_ACTIVE,
    DOC_STATUS_DELETED,
    KnowledgeDocumentORM,
)


def get_by_doc_id(session: Session, doc_id: str) -> KnowledgeDocumentORM | None:
    return (
        session.query(KnowledgeDocumentORM)
        .filter(KnowledgeDocumentORM.doc_id == doc_id)
        .first()
    )


def list_all(
    session: Session,
    *,
    include_deleted: bool = False,
) -> list[KnowledgeDocumentORM]:
    query = session.query(KnowledgeDocumentORM).order_by(
        KnowledgeDocumentORM.updated_at.desc()
    )
    if not include_deleted:
        query = query.filter(KnowledgeDocumentORM.status == DOC_STATUS_ACTIVE)
    return query.all()


def upsert_active(
    session: Session,
    *,
    doc_id: str,
    filename: str,
    file_hash: str,
    chunk_count: int,
    file_path: str,
    operator_user_id: int | None,
    version: int,
) -> KnowledgeDocumentORM:
    row = get_by_doc_id(session, doc_id)
    if row is None:
        row = KnowledgeDocumentORM(
            doc_id=doc_id,
            filename=filename,
            file_hash=file_hash,
            version=version,
            chunk_count=chunk_count,
            file_path=file_path,
            status=DOC_STATUS_ACTIVE,
            operator_user_id=operator_user_id,
        )
        session.add(row)
    else:
        row.filename = filename
        row.file_hash = file_hash
        row.version = version
        row.chunk_count = chunk_count
        row.file_path = file_path
        row.status = DOC_STATUS_ACTIVE
        row.operator_user_id = operator_user_id
    session.flush()
    session.refresh(row)
    return row


def mark_deleted(session: Session, doc_id: str) -> KnowledgeDocumentORM | None:
    row = get_by_doc_id(session, doc_id)
    if row is None:
        return None
    row.status = DOC_STATUS_DELETED
    row.chunk_count = 0
    session.flush()
    session.refresh(row)
    return row
