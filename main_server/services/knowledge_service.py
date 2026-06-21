from __future__ import annotations

from pathlib import Path
from typing import Any

import main_server.Knowledge.ingest as ingest_module
import main_server.Knowledge.retriever as retriever_module
from main_server.Knowledge.doc_registry import (
    get_document as get_document_record,
    list_documents as list_document_records,
    mark_document_deleted,
)
from main_server.Knowledge.retriever import invalidate_index_cache
from main_server.Knowledge.vector_store import get_vector_store
from main_server.config.settings import get_settings
from main_server.core.audit import audit_log
from main_server.core.exceptions import KnowledgeError, NotFoundError
from main_server.DB import db_session
from main_server.DB.models import User

_EMPTY_MESSAGE = (
    "知识库中未找到与您问题相关的内容。"
    "请换一种问法，或联系管理员补充相关制度文档。"
)

_CATEGORY_MAP = {
    ".pdf": "PDF",
    ".docx": "Word",
    ".doc": "Word",
    ".txt": "文本",
    ".md": "Markdown",
}

_STATUS_LABELS = {
    "active": "已完成",
    "processing": "处理中",
    "failed": "失败",
}


def _guess_category(filename: str) -> str:
    return _CATEGORY_MAP.get(Path(filename).suffix.lower(), "其他")


def _file_size_bytes(file_path: str) -> int:
    path = Path(file_path)
    if path.is_file():
        return path.stat().st_size
    return 0


def _format_file_size(size: int) -> str:
    if size <= 0:
        return "-"
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _resolve_operator_name(user_id: int | None) -> str:
    if user_id is None:
        return "-"
    with db_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            return user.display_name or user.username
    return "-"


def _enrich_document(item: dict[str, Any]) -> dict[str, Any]:
    size = _file_size_bytes(item.get("file_path", ""))
    status = item.get("status", "active")
    return {
        **item,
        "category": _guess_category(item.get("filename", "")),
        "file_size": size,
        "file_size_label": _format_file_size(size),
        "operator_name": _resolve_operator_name(item.get("operator_user_id")),
        "status_label": _STATUS_LABELS.get(status, status),
    }


class KnowledgeService:
    """知识库业务层：导入、检索、为 Agent 提供上下文。"""

    def ingest_file(
        self,
        file_path: str | Path,
        *,
        operator_user_id: int | None = None,
        logical_name: str | None = None,
    ) -> dict[str, Any]:
        result = ingest_module.ingest_file(
            file_path,
            operator_user_id=operator_user_id,
            logical_name=logical_name,
        )
        if not result.get("unchanged"):
            audit_log(
                "knowledge.ingest",
                resource=result.get("doc_id", ""),
                detail=result.get("filename", ""),
                extra={
                    "version": result.get("version"),
                    "chunks": result.get("chunks"),
                },
            )
        return result

    def ingest_directory(
        self,
        directory: str | Path | None = None,
        *,
        operator_user_id: int | None = None,
    ) -> dict[str, Any]:
        result = ingest_module.ingest_directory(
            directory,
            operator_user_id=operator_user_id,
        )
        audit_log(
            "knowledge.ingest_directory",
            resource=str(result.get("directory", "")),
            detail=f"files={result.get('files')} chunks={result.get('chunks')}",
        )
        return result

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        keyword = query.strip()
        if not keyword:
            raise KnowledgeError(
                "检索内容不能为空", code="VALIDATION_ERROR", status_code=400
            )
        return retriever_module.search(query=keyword, top_k=top_k)

    def search_for_agent(
        self, query: str, top_k: int | None = None
    ) -> dict[str, Any]:
        """Agent 知识库检索：含 citation、空结果拒答。"""
        settings = get_settings()
        docs = self.search(query, top_k=top_k)
        q = query.strip()

        if docs:
            audit_log(
                "knowledge.search",
                resource="query",
                detail=f"hits={len(docs)} query={q[:80]}",
            )
        else:
            audit_log(
                "knowledge.search",
                resource="query",
                detail=f"hits=0 query={q[:80]}",
            )

        if not docs and settings.knowledge.reject_empty:
            return self._empty_rejection(query)

        citations = self._build_citations(docs)
        context = self._build_context_from_docs(docs, citations) if docs else ""
        return {
            "query": query,
            "docs": docs,
            "citations": citations,
            "context": context,
            "rejected": False,
            "citation_required": True,
        }

    def _empty_rejection(self, query: str) -> dict[str, Any]:
        return {
            "query": query,
            "docs": [],
            "citations": [],
            "context": "",
            "rejected": True,
            "error": "no_results",
            "message": _EMPTY_MESSAGE,
            "citation_required": False,
        }

    def _build_citations(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        citations: list[dict[str, Any]] = []
        for index, doc in enumerate(docs, start=1):
            metadata = doc.get("metadata") or {}
            source = metadata.get("source", "unknown")
            page = metadata.get("page")
            snippet = (doc.get("content") or "").strip()
            if len(snippet) > 120:
                snippet = snippet[:120] + "…"
            citations.append(
                {
                    "index": index,
                    "ref": f"[{index}]",
                    "source": source,
                    "page": page if page else None,
                    "snippet": snippet,
                    "score": doc.get("rerank_score") or doc.get("score"),
                }
            )
        return citations

    def _build_context_from_docs(
        self,
        docs: list[dict[str, Any]],
        citations: list[dict[str, Any]] | None = None,
    ) -> str:
        if citations is None:
            citations = self._build_citations(docs)

        parts: list[str] = [
            "以下检索片段供回答引用，回复时必须标注引用编号如 [1]、[2]："
        ]
        for citation, doc in zip(citations, docs):
            page = citation.get("page")
            page_info = f" 页码:{page}" if page else ""
            parts.append(
                f"{citation['ref']} 来源:{citation['source']}{page_info}\n"
                f"{doc.get('content', '').strip()}"
            )
        return "\n\n".join(parts)

    def build_context(self, query: str, top_k: int | None = None) -> str:
        """将检索结果拼成 Agent 可用的上下文文本。"""
        result = self.search_for_agent(query, top_k=top_k)
        if result.get("rejected"):
            raise KnowledgeError(
                result.get("message", _EMPTY_MESSAGE),
                code="NOT_FOUND",
                status_code=404,
            )
        return result["context"]

    def stats(self) -> dict[str, Any]:
        settings = get_settings()
        store = get_vector_store()
        documents = list_document_records()
        last_updated = None
        if documents:
            latest = max(
                (d.updated_at for d in documents if d.updated_at),
                default=None,
            )
            if latest:
                last_updated = latest.isoformat()
        kb_status = "正常" if documents else "空库"
        return {
            "collection": settings.knowledge.collection_name,
            "chroma_path": str(settings.knowledge.abs_chroma_path),
            "docs_path": str(settings.knowledge.abs_docs_path),
            "chunk_count": store.count(),
            "document_count": len(documents),
            "last_updated": last_updated,
            "kb_status": kb_status,
            "top_k": settings.knowledge.top_k,
            "rerank_enabled": settings.knowledge.rerank_enabled,
            "hybrid_enabled": settings.knowledge.hybrid_enabled,
        }

    def list_documents(self) -> list[dict[str, Any]]:
        return [_enrich_document(item.to_dict()) for item in list_document_records()]

    def get_document(self, doc_id: str) -> dict[str, Any]:
        record = get_document_record(doc_id)
        if record is None or record.status != "active":
            raise NotFoundError(f"知识库文档不存在: {doc_id}")
        return _enrich_document(record.to_dict())

    def get_document_detail(self, doc_id: str) -> dict[str, Any]:
        base = self.get_document(doc_id)
        chunks = get_vector_store().get_chunks_by_doc_id(doc_id, limit=5)
        base["chunk_previews"] = [
            (c.get("content") or "").strip() for c in chunks if c.get("content")
        ]
        base["vector_count"] = base.get("chunk_count", 0)
        return base

    def rebuild_index(self, *, operator_user_id: int | None = None) -> dict[str, Any]:
        invalidate_index_cache()
        result = self.ingest_directory(operator_user_id=operator_user_id)
        audit_log(
            "knowledge.rebuild",
            resource="index",
            detail=f"files={result.get('files')} chunks={result.get('chunks')}",
        )
        return result

    def delete_document(
        self,
        doc_id: str,
        *,
        operator_user_id: int | None = None,
    ) -> dict[str, Any]:
        record = get_document_record(doc_id)
        if record is None or record.status != "active":
            raise NotFoundError(f"知识库文档不存在: {doc_id}")

        removed_chunks = get_vector_store().delete_by_doc_id(doc_id)
        invalidate_index_cache()
        mark_document_deleted(doc_id)
        audit_log(
            "knowledge.delete",
            resource=doc_id,
            detail=record.filename,
            extra={"removed_chunks": removed_chunks, "operator_user_id": operator_user_id},
        )
        return {
            "doc_id": doc_id,
            "filename": record.filename,
            "removed_chunks": removed_chunks,
            "status": "deleted",
        }


knowledge_service = KnowledgeService()
