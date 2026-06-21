from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field

from main_server.config.settings import get_settings
from main_server.api.deps.auth_dep import (
    CurrentUser,
    require_admin,
    require_business_user,
)
from main_server.core.logger import logger
from main_server.services.knowledge_service import knowledge_service

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+")


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)


class KnowledgeSearchResponse(BaseModel):
    query: str
    docs: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    context: str
    rejected: bool = False
    error: str | None = None
    message: str | None = None


class KnowledgeIngestResponse(BaseModel):
    result: dict[str, Any]


class KnowledgeDocumentListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int


class KnowledgeDeleteResponse(BaseModel):
    doc_id: str
    filename: str
    removed_chunks: int
    status: str


def _sanitize_filename(name: str) -> str:
    cleaned = _SAFE_FILENAME.sub("_", name.strip())
    return cleaned or "upload.txt"


@router.get("/stats")
def knowledge_stats(_: CurrentUser = Depends(require_business_user)):
    return knowledge_service.stats()


@router.get("/docs", response_model=KnowledgeDocumentListResponse)
def list_knowledge_documents(_: CurrentUser = Depends(require_business_user)):
    items = knowledge_service.list_documents()
    return KnowledgeDocumentListResponse(items=items, total=len(items))


@router.get("/docs/{doc_id}")
def get_knowledge_document(
    doc_id: str,
    _: CurrentUser = Depends(require_business_user),
):
    return knowledge_service.get_document_detail(doc_id)


@router.post("/rebuild", response_model=KnowledgeIngestResponse)
def rebuild_knowledge_index(
    current_user: CurrentUser = Depends(require_admin),
):
    result = knowledge_service.rebuild_index(operator_user_id=current_user.user_id)
    logger.info("api.knowledge.rebuild files=%s chunks=%s", result.get("files"), result.get("chunks"))
    return KnowledgeIngestResponse(result=result)


@router.delete("/docs/{doc_id}", response_model=KnowledgeDeleteResponse)
def delete_knowledge_document(
    doc_id: str,
    current_user: CurrentUser = Depends(require_admin),
):
    result = knowledge_service.delete_document(
        doc_id,
        operator_user_id=current_user.user_id,
    )
    logger.info(
        "api.knowledge.delete doc_id=%s filename=%s removed_chunks=%s",
        result["doc_id"],
        result["filename"],
        result["removed_chunks"],
    )
    return KnowledgeDeleteResponse(**result)


@router.post("/search", response_model=KnowledgeSearchResponse)
def knowledge_search(
    body: KnowledgeSearchRequest,
    _: CurrentUser = Depends(require_business_user),
):
    result = knowledge_service.search_for_agent(body.query, top_k=body.top_k)
    return KnowledgeSearchResponse(**result)


@router.post("/ingest/directory", response_model=KnowledgeIngestResponse)
def ingest_directory(
    current_user: CurrentUser = Depends(require_admin),
):
    result = knowledge_service.ingest_directory(operator_user_id=current_user.user_id)
    logger.info("api.knowledge.ingest_directory files=%s", result.get("files"))
    return KnowledgeIngestResponse(result=result)


@router.post("/ingest/file", response_model=KnowledgeIngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_admin),
):
    settings = get_settings()
    upload_dir = settings.knowledge.abs_docs_path / "_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    original_name = _sanitize_filename(file.filename or "upload.txt")
    suffix = Path(original_name).suffix or ".txt"
    stored_name = f"{Path(original_name).stem}_{uuid.uuid4().hex[:8]}{suffix}"
    dest = upload_dir / stored_name
    dest.write_bytes(await file.read())
    result = knowledge_service.ingest_file(
        dest,
        operator_user_id=current_user.user_id,
        logical_name=original_name,
    )
    logger.info(
        "api.knowledge.ingest_file doc_id=%s file=%s chunks=%s version=%s",
        result.get("doc_id"),
        original_name,
        result.get("chunks"),
        result.get("version"),
    )
    return KnowledgeIngestResponse(result=result)
