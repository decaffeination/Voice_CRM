from __future__ import annotations

import asyncio
import io
import time
import wave
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import torch

from main_server.config.settings import get_settings
from main_server.core.exceptions import ConfigError, ValidationError
from main_server.core.logger import logger
from main_server.core.provider_errors import raise_tts_error
from main_server.core.provider_retry import call_with_retry
from main_server.providers.TTS.base import BaseTTS
from main_server.utils.download_chattts_model import ensure_chattts_model_local

_PROVIDER = "chattts"
_SAMPLE_RATE = 24_000


def _resolve_tts_device(configured: str) -> str:
    """解析 TTS 运行设备；配置 cuda 但不可用时回退 cpu 并打日志。"""
    device = (configured or "cpu").strip().lower()
    if device in ("cuda", "gpu"):
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            logger.info("TTS 使用 GPU device=cuda name=%s", name)
            return "cuda"
        logger.warning(
            "config 指定 device=cuda，但当前 PyTorch 不可用 CUDA，已回退 device=cpu。"
            "请安装 CUDA 版 PyTorch 并确认显卡驱动正常。"
        )
        return "cpu"
    return device


def _load_chat_model(chat: Any, *, model_path: Path, compile: bool, device: str) -> bool:
    base_kwargs: dict[str, Any] = {
        "compile": compile,
        "source": "custom",
        "custom_path": str(model_path),
    }
    for kwargs in (base_kwargs | {"device": device}, base_kwargs):
        try:
            return bool(chat.load(**kwargs))
        except TypeError:
            continue
    return False


@lru_cache
def _get_chat_model() -> Any:
    import ChatTTS

    settings = get_settings()
    tts = settings.models.tts
    model_path = ensure_chattts_model_local()
    device = _resolve_tts_device(tts.device)

    chat = ChatTTS.Chat()
    loaded = _load_chat_model(
        chat,
        model_path=model_path,
        compile=tts.compile,
        device=device,
    )
    if not loaded:
        raise ConfigError("ChatTTS 模型加载失败")

    logger.info(
        "加载 ChatTTS 模型 path=%s device=%s compile=%s",
        model_path,
        device,
        tts.compile,
    )
    return chat


def _resolve_speaker(chat: Any, voice: str | None) -> Any:
    settings = get_settings()
    seed_text = (voice or settings.models.tts.voice or "").strip()
    if seed_text.isdigit():
        torch.manual_seed(int(seed_text))
    return chat.sample_random_speaker()


def _wav_to_bytes(wav: Any) -> bytes:
    """ChatTTS float32 波形 -> 16-bit PCM WAV 字节。

    用标准库 wave 写，避免新版 torchaudio.save 依赖 torchcodec。
    """
    audio = np.asarray(wav, dtype=np.float32).reshape(-1)
    audio = np.clip(audio, -1.0, 1.0)
    pcm16 = (audio * 32767.0).astype("<i2").tobytes()

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm16)
    return buffer.getvalue()


class ChatTTSProvider(BaseTTS):
    def __init__(self) -> None:
        self._chat = _get_chat_model()
        self._speaker = _resolve_speaker(self._chat, None)

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        content = text.strip()
        if not content:
            raise ValidationError("TTS 文本不能为空")

        speaker = (
            _resolve_speaker(self._chat, voice) if voice is not None else self._speaker
        )

        def do_synthesize() -> bytes:
            import ChatTTS

            params = ChatTTS.Chat.InferCodeParams(spk_emb=speaker)
            wavs = self._chat.infer([content], params_infer_code=params)
            if not wavs:
                raise RuntimeError("ChatTTS 未返回音频")
            return _wav_to_bytes(wavs[0])

        text_len = len(content)
        start = time.perf_counter()
        try:
            audio_bytes = await asyncio.to_thread(
                call_with_retry,
                do_synthesize,
                provider=_PROVIDER,
                retryable=(),
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
