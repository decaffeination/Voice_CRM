from __future__ import annotations

import importlib
import importlib.util
import time
from pathlib import Path

from main_server.config.settings import get_settings
from main_server.core.logger import logger
from main_server.core.provider_errors import raise_tts_error
from main_server.core.provider_retry import async_call_with_retry
from main_server.providers.TTS.base import BaseTTS

_PROVIDER = "edge-tts"
_TTS_RETRYABLE = (ConnectionError, OSError)
_EDGE_TTS_SDK = "edge_tts"
_PROVIDER_FILE = Path(__file__).resolve()


def _load_edge_tts_sdk():
    """加载 pip 包 edge-tts；校验 spec，避免误加载本目录下的 provider 模块。"""
    spec = importlib.util.find_spec(_EDGE_TTS_SDK)
    if spec is None or not spec.origin:
        raise ModuleNotFoundError(
            f"未安装 {_EDGE_TTS_SDK}，请执行: pip install edge-tts"
        )
    origin = Path(spec.origin).resolve()
    if origin == _PROVIDER_FILE:
        raise RuntimeError(
            "edge-tts SDK 被本地 provider 模块遮蔽，请检查 Python 导入路径"
        )
    module = importlib.import_module(_EDGE_TTS_SDK)
    if not hasattr(module, "Communicate"):
        raise RuntimeError(f"模块 {_EDGE_TTS_SDK!r} 缺少 Communicate")
    return module


class EdgeTTSProvider(BaseTTS):
    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        settings = get_settings()
        voice_name = voice or settings.models.tts.voice

        async def do_synthesize() -> bytes:
            edge_tts_sdk = _load_edge_tts_sdk()
            communicate = edge_tts_sdk.Communicate(text, voice_name)
            audio_bytes = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes += chunk["data"]
            return audio_bytes

        text_len = len(text)
        start = time.perf_counter()
        try:
            audio_bytes = await async_call_with_retry(
                do_synthesize,
                provider=_PROVIDER,
                retryable=_TTS_RETRYABLE,
            )
        except Exception as exc:
            raise_tts_error(exc, provider=_PROVIDER)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "tts.synthesize provider=%s duration_ms=%.1f text_len=%s audio_bytes=%s",
            _PROVIDER,
            duration_ms,
            text_len,
            len(audio_bytes),
        )
        return audio_bytes
