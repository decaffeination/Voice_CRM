from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from main_server.api.deps.auth_dep import CurrentUser, require_business_user
from main_server.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class DashboardOverviewResponse(BaseModel):
    overview: dict[str, Any]
    ai_runtime: dict[str, Any]
    knowledge: dict[str, Any]
    crm: dict[str, Any]
    recent_activities: list[dict[str, Any]]
    system_status: list[dict[str, Any]]


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    current_user: CurrentUser = Depends(require_business_user),
):
    data = dashboard_service.get_overview(
        user_id=current_user.user_id,
        roles=current_user.roles,
    )
    return DashboardOverviewResponse(**data)
