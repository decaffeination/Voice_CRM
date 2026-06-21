"""Provider 异常分类与映射。"""

from __future__ import annotations

import httpx

from main_server.core.exceptions import (
    ASRError,
    ASRTimeoutError,
    LLMConnectionError,
    LLMError,
    LLMTimeoutError,
    TTSConnectionError,
    TTSError,
    TTSTimeoutError,
)


def is_timeout(exc: BaseException) -> bool:
    return isinstance(exc, (TimeoutError, httpx.TimeoutException))


def is_connection_error(exc: BaseException) -> bool:
    if isinstance(exc, (ConnectionError, httpx.ConnectError, OSError)):
        return True
    exc_name = type(exc).__name__
    return exc_name in {"ClientConnectorError", "ClientConnectionError"}


def raise_llm_error(exc: BaseException, *, provider: str) -> None:
    if is_timeout(exc):
        raise LLMTimeoutError(provider=provider) from exc
    if is_connection_error(exc):
        raise LLMConnectionError(provider=provider) from exc
    raise LLMError("LLM 调用失败", provider=provider) from exc


def raise_asr_error(exc: BaseException, *, provider: str) -> None:
    if is_timeout(exc):
        raise ASRTimeoutError(provider=provider) from exc
    raise ASRError("ASR 识别失败", provider=provider) from exc


def raise_tts_error(exc: BaseException, *, provider: str) -> None:
    if is_timeout(exc):
        raise TTSTimeoutError(provider=provider) from exc
    if is_connection_error(exc):
        raise TTSConnectionError(provider=provider) from exc
    raise TTSError("TTS 合成失败", provider=provider) from exc
