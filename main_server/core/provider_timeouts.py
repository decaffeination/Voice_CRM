"""各 Provider 超时配置解析。"""

from __future__ import annotations

from main_server.config.settings import get_settings

_PROVIDER_KEYS = frozenset(
    {"llm", "asr", "tts", "pipeline", "knowledge", "ws", "default"}
)


def resolve_provider_timeout(provider: str) -> float:
    """按 provider 名称返回超时秒数；未知 provider 回退到 providers.timeout_seconds。"""
    settings = get_settings()
    providers = settings.providers
    key = _normalize_provider_key(provider)

    if key == "llm":
        return providers.llm_timeout_seconds
    if key == "asr":
        return providers.asr_timeout_seconds
    if key == "tts":
        return providers.tts_timeout_seconds
    if key == "pipeline":
        return providers.pipeline_timeout_seconds
    if key == "knowledge":
        return settings.knowledge.timeout_seconds
    if key == "ws":
        return providers.ws_idle_timeout_seconds
    return providers.timeout_seconds


def _normalize_provider_key(provider: str) -> str:
    normalized = provider.strip().lower()
    aliases = {
        "deepseek": "llm",
        "funasr": "asr",
        "chattts": "tts",
        "edge-tts": "tts",
        "edge_tts": "tts",
    }
    key = aliases.get(normalized, normalized)
    if key in _PROVIDER_KEYS:
        return key
    return "default"
