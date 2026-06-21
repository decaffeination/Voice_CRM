"""注册内置 Provider 实现。"""

from __future__ import annotations

from main_server.providers.ASR.base import BaseASR
from main_server.providers.LLM.base import BaseLLM
from main_server.providers.registry import register_asr, register_llm, register_tts
from main_server.providers.TTS.base import BaseTTS


def _create_deepseek_llm() -> BaseLLM:
    from main_server.providers.LLM.deepseek import DeepSeekLLM

    return DeepSeekLLM()


def _create_funasr() -> BaseASR:
    from main_server.providers.ASR.funasr import FunASRProvider

    return FunASRProvider()


def _create_edge_tts() -> BaseTTS:
    from main_server.providers.TTS.edge_tts import EdgeTTSProvider

    return EdgeTTSProvider()


def _create_chattts() -> BaseTTS:
    from main_server.providers.TTS.chattts import ChatTTSProvider

    return ChatTTSProvider()


def register_default_providers() -> None:
    """注册内置 Provider；工厂内延迟 import，避免热重载绑定旧类。"""
    register_llm("deepseek", _create_deepseek_llm)
    register_asr("funasr", _create_funasr)
    register_tts("chattts", _create_chattts)
    register_tts("edge-tts", _create_edge_tts)


def refresh_default_providers() -> None:
    """启动或热重载后刷新注册与实例缓存。"""
    from main_server.providers.registry import reset_provider_instances

    register_default_providers()
    reset_provider_instances()


register_default_providers()
