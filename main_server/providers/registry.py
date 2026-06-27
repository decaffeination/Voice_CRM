"""Provider 注册表与运行时工厂（配置驱动切换）。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from main_server.config.settings import get_settings
from main_server.core.exceptions import ConfigError
from main_server.providers.ASR.base import BaseASR
from main_server.providers.LLM.base import BaseLLM
from main_server.providers.TTS.base import BaseTTS

T = TypeVar("T")
Factory = Callable[[], T]

_llm_factories: dict[str, Factory[BaseLLM]] = {}
_asr_factories: dict[str, Factory[BaseASR]] = {}
_tts_factories: dict[str, Factory[BaseTTS]] = {}

_llm_instances: dict[str, BaseLLM] = {}
_asr_instances: dict[str, BaseASR] = {}
_tts_instances: dict[str, BaseTTS] = {}


def register_llm(name: str, factory: Factory[BaseLLM]) -> None:
    _llm_factories[name.strip()] = factory


def register_asr(name: str, factory: Factory[BaseASR]) -> None:
    _asr_factories[name.strip()] = factory


def register_tts(name: str, factory: Factory[BaseTTS]) -> None:
    _tts_factories[name.strip()] = factory


def list_registered_providers() -> dict[str, list[str]]:
    return {
        "llm": sorted(_llm_factories),
        "asr": sorted(_asr_factories),
        "tts": sorted(_tts_factories),
    }


def _resolve_factory(
    *,
    kind: str,
    configured: str,
    factories: dict[str, Factory[T]],
) -> Factory[T]:
    name = configured.strip()
    factory = factories.get(name)
    if factory is None:
        available = ", ".join(sorted(factories)) or "-"
        raise ConfigError(
            f"不支持的 {kind} provider: {name}，可选: {available}"
        )
    return factory


def get_llm_provider() -> BaseLLM:
    from main_server.services.runtime_settings import runtime_settings

    name = runtime_settings.get_llm_settings().provider
    if name not in _llm_instances:
        factory = _resolve_factory(
            kind="LLM", configured=name, factories=_llm_factories
        )
        _llm_instances[name] = factory()
    return _llm_instances[name]


def get_asr_provider() -> BaseASR:
    name = get_settings().models.asr.provider
    if name not in _asr_instances:
        factory = _resolve_factory(
            kind="ASR", configured=name, factories=_asr_factories
        )
        _asr_instances[name] = factory()
    return _asr_instances[name]


def get_tts_provider() -> BaseTTS:
    name = get_settings().models.tts.provider
    if name not in _tts_instances:
        factory = _resolve_factory(
            kind="TTS", configured=name, factories=_tts_factories
        )
        _tts_instances[name] = factory()
    return _tts_instances[name]


def reset_provider_instances() -> None:
    """测试或热重载时清空实例缓存。"""
    _llm_instances.clear()
    _asr_instances.clear()
    _tts_instances.clear()
