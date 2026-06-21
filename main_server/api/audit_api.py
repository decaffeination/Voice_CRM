from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from main_server.api.deps.auth_dep import CurrentUser, require_admin
from main_server.services.audit_service import list_audit_logs

router = APIRouter(prefix="/api/admin", tags=["admin-audit"])


class AuditLogListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


@router.get("/audit", response_model=AuditLogListResponse)
def list_audit(
    user_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: CurrentUser = Depends(require_admin),
):
    items, total = list_audit_logs(
        user_id=user_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
