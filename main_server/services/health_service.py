"""Provider 健康检查。"""

from __future__ import annotations

from typing import Any

import httpx

from main_server.config.settings import get_settings
from main_server.DB import db_session
from main_server.DB.database_info import database_display_name
from main_server.DB.models import User
from main_server.providers import bootstrap as _bootstrap  # noqa: F401 — 注册默认实现
from main_server.providers.registry import list_registered_providers


def get_health_status() -> dict[str, Any]:
    settings = get_settings()
    llm = _check_llm(settings.llm.provider, settings.llm.base_url, settings.llm.api_key)
    asr = _check_asr(settings.models.asr.provider, settings.models.abs_asr_path)
    tts = _check_tts(settings.models.tts.provider)
    database = _check_database(settings.database.dialect)

    components = {"llm": llm, "asr": asr, "tts": tts, "database": database}
    overall = "ok"
    if any(item["status"] != "ok" for item in components.values()):
        overall = "degraded"

    return {
        "status": overall,
        "providers": list_registered_providers(),
        "active": {
            "llm": settings.llm.provider,
            "asr": settings.models.asr.provider,
            "tts": settings.models.tts.provider,
            "database": database_display_name(settings.database.dialect),
        },
        "components": components,
    }


def _check_database(dialect: str) -> dict[str, Any]:
    info: dict[str, Any] = {
        "dialect": dialect,
        "display_name": database_display_name(dialect),
        "status": "ok",
    }
    try:
        with db_session() as session:
            session.query(User).limit(1).first()
        info["connectivity"] = "reachable"
    except Exception as exc:
        info["status"] = "down"
        info["connectivity"] = "unreachable"
        info["detail"] = str(exc)
    return info


def _check_llm(provider: str, base_url: str, api_key: str) -> dict[str, Any]:
    info: dict[str, Any] = {"provider": provider, "status": "ok"}
    if not api_key:
        info["status"] = "degraded"
        info["detail"] = "未配置 LLM_API_KEY"
        return info

    url = base_url.rstrip("/")
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url)
        info["connectivity"] = "reachable"
        info["http_status"] = response.status_code
        if response.status_code >= 500:
            info["status"] = "degraded"
            info["detail"] = f"上游 HTTP {response.status_code}"
    except httpx.HTTPError as exc:
        info["status"] = "down"
        info["connectivity"] = "unreachable"
        info["detail"] = str(exc)
    return info


def _check_asr(provider: str, model_path) -> dict[str, Any]:
    info: dict[str, Any] = {"provider": provider, "status": "ok"}
    if model_path.exists():
        info["connectivity"] = "model_ready"
        info["model_path"] = str(model_path)
        return info
    info["status"] = "down"
    info["connectivity"] = "model_missing"
    info["detail"] = f"ASR 模型目录不存在: {model_path}"
    return info


def _check_tts(provider: str) -> dict[str, Any]:
    registered = list_registered_providers()["tts"]
    if provider in registered:
        return {
            "provider": provider,
            "status": "ok",
            "connectivity": "registered",
        }
    return {
        "provider": provider,
        "status": "down",
        "connectivity": "unregistered",
        "detail": f"TTS provider 未注册: {provider}",
    }
