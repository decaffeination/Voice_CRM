from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from main_server.api.deps.auth_dep import CurrentUser, require_admin
from main_server.services.runtime_settings import runtime_settings

router = APIRouter(prefix="/api/admin", tags=["admin-settings"])


class EmailSettingsResponse(BaseModel):
    enabled: bool
    dry_run: bool
    smtp_configured: bool
    from_address: str
    production_mode: bool


class EmailSettingsUpdateRequest(BaseModel):
    enabled: bool | None = None
    dry_run: bool | None = Field(
        default=None,
        description="true=测试模式（不实际发信）；false=生产模式（需 SMTP 已配置）",
    )


@router.get("/settings/email", response_model=EmailSettingsResponse)
def get_email_settings(_: CurrentUser = Depends(require_admin)):
    return EmailSettingsResponse(**runtime_settings.get_email_public_config())


@router.patch("/settings/email", response_model=EmailSettingsResponse)
def update_email_settings(
    body: EmailSettingsUpdateRequest,
    current_user: CurrentUser = Depends(require_admin),
):
    config = runtime_settings.update_email_settings(
        enabled=body.enabled,
        dry_run=body.dry_run,
        operator_user_id=current_user.user_id,
    )
    return EmailSettingsResponse(**config)
