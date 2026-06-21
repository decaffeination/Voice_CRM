from __future__ import annotations

import threading
from typing import Any

from main_server.config.settings import EmailToolSettings, get_settings
from main_server.core.audit import audit_log


class RuntimeSettingsService:
    """运行时配置覆盖层（进程内）；YAML 为默认值，Admin 可热更新邮件开关。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._email_overrides: dict[str, Any] = {}

    def get_email_settings(self) -> EmailToolSettings:
        base = get_settings().tools.email.model_copy(deep=True)
        with self._lock:
            overrides = dict(self._email_overrides)
        if not overrides:
            return base
        return base.model_copy(update=overrides)

    def get_email_public_config(self) -> dict[str, Any]:
        settings = self.get_email_settings()
        return {
            "enabled": settings.enabled,
            "dry_run": settings.dry_run,
            "smtp_configured": bool(settings.smtp_host),
            "from_address": settings.from_address,
            "production_mode": settings.enabled and not settings.dry_run and bool(
                settings.smtp_host
            ),
        }

    def update_email_settings(
        self,
        *,
        enabled: bool | None = None,
        dry_run: bool | None = None,
        operator_user_id: int | None = None,
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        if enabled is not None:
            updates["enabled"] = enabled
        if dry_run is not None:
            updates["dry_run"] = dry_run
        if not updates:
            return self.get_email_public_config()

        before = self.get_email_public_config()
        with self._lock:
            self._email_overrides.update(updates)
        after = self.get_email_public_config()

        audit_log(
            "settings.email_update",
            resource="email",
            detail=f"before={before} after={after}",
            extra={"operator_user_id": operator_user_id},
        )
        return after


runtime_settings = RuntimeSettingsService()
