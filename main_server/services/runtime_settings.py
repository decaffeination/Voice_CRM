from __future__ import annotations

import threading
from typing import Any

from main_server.config.settings import EmailToolSettings, LLMSettings, get_settings
from main_server.core.audit import audit_log
from main_server.providers.registry import list_registered_providers, reset_provider_instances


class RuntimeSettingsService:
    """运行时配置覆盖层（进程内）；YAML 为默认值，Admin 可热更新。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._email_overrides: dict[str, Any] = {}
        self._system_overrides: dict[str, Any] = {}
        self._llm_overrides: dict[str, Any] = {}

    def clear_all_overrides(self) -> None:
        with self._lock:
            self._email_overrides.clear()
            self._system_overrides.clear()
            self._llm_overrides.clear()

    # ------------------------------------------------------------------ email
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
            "smtp_host": settings.smtp_host,
            "smtp_port": settings.smtp_port,
            "smtp_user": settings.smtp_user,
            "smtp_password_set": bool(settings.smtp_password),
            "from_address": settings.from_address,
            "use_tls": settings.use_tls,
            "production_mode": settings.enabled
            and not settings.dry_run
            and bool(settings.smtp_host),
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
        self._audit_settings("settings.email_update", "email", before, after, operator_user_id)
        return after

    def update_smtp_settings(
        self,
        *,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        from_address: str | None = None,
        use_tls: bool | None = None,
        operator_user_id: int | None = None,
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        if smtp_host is not None:
            updates["smtp_host"] = smtp_host.strip()
        if smtp_port is not None:
            updates["smtp_port"] = smtp_port
        if smtp_user is not None:
            updates["smtp_user"] = smtp_user.strip()
        if smtp_password is not None:
            updates["smtp_password"] = smtp_password
        if from_address is not None:
            updates["from_address"] = from_address.strip()
        if use_tls is not None:
            updates["use_tls"] = use_tls
        if not updates:
            return self.get_email_public_config()

        before = self.get_email_public_config()
        with self._lock:
            self._email_overrides.update(updates)
        after = self.get_email_public_config()
        self._audit_settings("settings.smtp_update", "email", before, after, operator_user_id)
        return after

    # ------------------------------------------------------------------ system
    def get_system_params(self) -> dict[str, Any]:
        settings = get_settings()
        defaults = {
            "system_name": settings.app.name,
            "system_logo": "",
            "default_language": "zh-CN",
            "token_limit": 8192,
            "session_retention_days": 90,
        }
        with self._lock:
            overrides = dict(self._system_overrides)
        if overrides:
            defaults.update(overrides)
        return defaults

    def update_system_params(
        self,
        *,
        system_name: str | None = None,
        system_logo: str | None = None,
        default_language: str | None = None,
        token_limit: int | None = None,
        session_retention_days: int | None = None,
        operator_user_id: int | None = None,
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        if system_name is not None:
            updates["system_name"] = system_name.strip()
        if system_logo is not None:
            updates["system_logo"] = system_logo.strip()
        if default_language is not None:
            updates["default_language"] = default_language.strip()
        if token_limit is not None:
            updates["token_limit"] = token_limit
        if session_retention_days is not None:
            updates["session_retention_days"] = session_retention_days
        if not updates:
            return self.get_system_params()

        before = self.get_system_params()
        with self._lock:
            self._system_overrides.update(updates)
        after = self.get_system_params()
        self._audit_settings(
            "settings.system_update", "system", before, after, operator_user_id
        )
        return after

    # ------------------------------------------------------------------ llm
    def get_llm_settings(self) -> LLMSettings:
        base = get_settings().llm.model_copy(deep=True)
        with self._lock:
            overrides = {
                k: v for k, v in self._llm_overrides.items() if k in LLMSettings.model_fields
            }
        if overrides:
            return base.model_copy(update=overrides)
        return base

    def get_llm_public_config(self) -> dict[str, Any]:
        llm = self.get_llm_settings()
        with self._lock:
            extras = dict(self._llm_overrides)
        temperature = float(extras.get("temperature", 0.7))
        max_tokens = int(extras.get("max_tokens", 4096))
        enabled = bool(extras.get("enabled", True))
        providers = list_registered_providers()["llm"]
        return {
            "provider": llm.provider,
            "model": llm.model,
            "base_url": llm.base_url,
            "api_key_configured": bool(llm.api_key),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "enabled": enabled,
            "is_default": True,
            "available_providers": providers,
        }

    def list_model_configs(self) -> list[dict[str, Any]]:
        cfg = self.get_llm_public_config()
        name_map = {
            "deepseek": "DeepSeek",
            "openai": "OpenAI",
            "qwen": "通义千问",
        }
        return [
            {
                "id": cfg["provider"],
                "name": name_map.get(cfg["provider"], cfg["provider"]),
                "provider": name_map.get(cfg["provider"], cfg["provider"]),
                "model": cfg["model"],
                "temperature": cfg["temperature"],
                "max_tokens": cfg["max_tokens"],
                "enabled": cfg["enabled"],
                "is_default": True,
                "base_url": cfg["base_url"],
                "api_key_configured": cfg["api_key_configured"],
            }
        ]

    def update_llm_settings(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        enabled: bool | None = None,
        operator_user_id: int | None = None,
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        llm_updates: dict[str, Any] = {}
        if provider is not None:
            name = provider.strip()
            available = list_registered_providers()["llm"]
            if name not in available:
                from main_server.core.exceptions import ValidationError

                raise ValidationError(
                    f"不支持的 LLM provider: {name}，可选: {', '.join(available)}"
                )
            llm_updates["provider"] = name
        if model is not None:
            llm_updates["model"] = model.strip()
        if base_url is not None:
            llm_updates["base_url"] = base_url.strip()
        if temperature is not None:
            updates["temperature"] = temperature
        if max_tokens is not None:
            updates["max_tokens"] = max_tokens
        if enabled is not None:
            updates["enabled"] = enabled

        if not llm_updates and not updates:
            return self.get_llm_public_config()

        before = self.get_llm_public_config()
        with self._lock:
            self._llm_overrides.update(updates)
            self._llm_overrides.update(llm_updates)
        reset_provider_instances()
        after = self.get_llm_public_config()
        self._audit_settings("settings.llm_update", "llm", before, after, operator_user_id)
        return after

    @staticmethod
    def _audit_settings(
        action: str,
        resource: str,
        before: dict[str, Any],
        after: dict[str, Any],
        operator_user_id: int | None,
    ) -> None:
        audit_log(
            action,
            resource=resource,
            detail=f"before={before} after={after}",
            extra={"operator_user_id": operator_user_id},
        )


runtime_settings = RuntimeSettingsService()
