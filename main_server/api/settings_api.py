from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from main_server.api.deps.auth_dep import CurrentUser, require_admin
from main_server.providers.Tools.email_tool import get_email_provider
from main_server.services.runtime_settings import runtime_settings

router = APIRouter(prefix="/api/admin", tags=["admin-settings"])


class EmailSettingsResponse(BaseModel):
    enabled: bool
    dry_run: bool
    smtp_configured: bool
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password_set: bool = False
    from_address: str
    use_tls: bool = True
    production_mode: bool


class EmailSettingsUpdateRequest(BaseModel):
    enabled: bool | None = None
    dry_run: bool | None = Field(
        default=None,
        description="true=测试模式（不实际发信）；false=生产模式（需 SMTP 已配置）",
    )


class SmtpSettingsUpdateRequest(BaseModel):
    smtp_host: str | None = None
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_user: str | None = None
    smtp_password: str | None = Field(
        default=None,
        description="留空或不传则保持原密码",
    )
    from_address: str | None = None
    use_tls: bool | None = None


class EmailTestRequest(BaseModel):
    to: str = Field(..., min_length=3, description="测试收件邮箱")


class EmailTestResponse(BaseModel):
    sent: bool
    dry_run: bool = False
    message_id: str | None = None
    error: str | None = None


class SystemParamsResponse(BaseModel):
    system_name: str
    system_logo: str
    default_language: str
    token_limit: int
    session_retention_days: int


class SystemParamsUpdateRequest(BaseModel):
    system_name: str | None = Field(default=None, max_length=128)
    system_logo: str | None = Field(default=None, max_length=512)
    default_language: str | None = Field(default=None, max_length=16)
    token_limit: int | None = Field(default=None, ge=1024, le=128000)
    session_retention_days: int | None = Field(default=None, ge=1, le=365)


class ModelConfigItem(BaseModel):
    id: str
    name: str
    provider: str
    model: str
    temperature: float
    max_tokens: int
    enabled: bool
    is_default: bool
    base_url: str = ""
    api_key_configured: bool = False


class ModelConfigListResponse(BaseModel):
    items: list[ModelConfigItem]


class ModelConfigUpdateRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=256, le=128000)
    enabled: bool | None = None


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


@router.patch("/settings/email/smtp", response_model=EmailSettingsResponse)
def update_smtp_settings(
    body: SmtpSettingsUpdateRequest,
    current_user: CurrentUser = Depends(require_admin),
):
    password = body.smtp_password if body.smtp_password else None
    config = runtime_settings.update_smtp_settings(
        smtp_host=body.smtp_host,
        smtp_port=body.smtp_port,
        smtp_user=body.smtp_user,
        smtp_password=password,
        from_address=body.from_address,
        use_tls=body.use_tls,
        operator_user_id=current_user.user_id,
    )
    return EmailSettingsResponse(**config)


@router.post("/settings/email/test", response_model=EmailTestResponse)
def test_email_send(
    body: EmailTestRequest,
    _: CurrentUser = Depends(require_admin),
):
    result = get_email_provider().send(
        to=body.to.strip(),
        subject="Voice-CRM SMTP 测试",
        body="这是一封来自 Voice-CRM 管理后台的测试邮件。",
    )
    return EmailTestResponse(
        sent=bool(result.get("sent")),
        dry_run=bool(result.get("dry_run")),
        message_id=result.get("message_id"),
        error=result.get("error"),
    )


@router.get("/settings/system", response_model=SystemParamsResponse)
def get_system_params(_: CurrentUser = Depends(require_admin)):
    return SystemParamsResponse(**runtime_settings.get_system_params())


@router.patch("/settings/system", response_model=SystemParamsResponse)
def update_system_params(
    body: SystemParamsUpdateRequest,
    current_user: CurrentUser = Depends(require_admin),
):
    params = runtime_settings.update_system_params(
        system_name=body.system_name,
        system_logo=body.system_logo,
        default_language=body.default_language,
        token_limit=body.token_limit,
        session_retention_days=body.session_retention_days,
        operator_user_id=current_user.user_id,
    )
    return SystemParamsResponse(**params)


@router.get("/settings/models", response_model=ModelConfigListResponse)
def list_model_configs(_: CurrentUser = Depends(require_admin)):
    items = [ModelConfigItem(**item) for item in runtime_settings.list_model_configs()]
    return ModelConfigListResponse(items=items)


@router.patch("/settings/models", response_model=ModelConfigListResponse)
def update_model_config(
    body: ModelConfigUpdateRequest,
    current_user: CurrentUser = Depends(require_admin),
):
    runtime_settings.update_llm_settings(
        provider=body.provider,
        model=body.model,
        base_url=body.base_url,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        enabled=body.enabled,
        operator_user_id=current_user.user_id,
    )
    items = [ModelConfigItem(**item) for item in runtime_settings.list_model_configs()]
    return ModelConfigListResponse(items=items)
