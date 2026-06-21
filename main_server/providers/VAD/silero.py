from __future__ import annotations

from functools import lru_cache

import numpy as np

from main_server.config.settings import get_settings
from main_server.core.exceptions import AppError, ProviderError
from main_server.core.logger import logger
from main_server.providers.VAD.base import BaseVAD
from main_server.utils.download_vad_model import ensure_vad_model_local


class SileroVADProvider(BaseVAD):
    """Silero VAD 流式检测，输入 16kHz mono int16 PCM。"""

    def __init__(self) -> None:
        settings = get_settings().models.vad
        self._sample_rate = settings.sample_rate
        self._window_samples = 512 if self._sample_rate == 16000 else 256
        self._window_bytes = self._window_samples * 2

        self._model = None
        self._iterator = None
        self._pcm_pending = bytearray()
        self._segment_pcm = bytearray()
        self._all_pcm = bytearray()
        self._collecting = False

        self._threshold = settings.threshold
        self._min_silence_ms = settings.min_silence_duration_ms

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return

        try:
            from silero_vad.utils_vad import OnnxWrapper, VADIterator

            model_path = ensure_vad_model_local()
            logger.info("加载本地 Silero VAD: %s", model_path)
            self._model = OnnxWrapper(str(model_path), force_onnx_cpu=True)
            self._iterator = VADIterator(
                self._model,
                threshold=self._threshold,
                sampling_rate=self._sample_rate,
                min_silence_duration_ms=self._min_silence_ms,
                speech_pad_ms=100,
            )
        except AppError:
            raise
        except Exception as exc:
            raise ProviderError("VAD 模型加载失败", provider="silero-vad") from exc

    def feed(self, pcm_bytes: bytes) -> list[bytes]:
        try:
            return self._feed_impl(pcm_bytes)
        except AppError:
            raise
        except Exception as exc:
            raise ProviderError("VAD 检测失败", provider="silero-vad") from exc

    def _feed_impl(self, pcm_bytes: bytes) -> list[bytes]:
        self._ensure_loaded()
        self._pcm_pending.extend(pcm_bytes)
        self._all_pcm.extend(pcm_bytes)
        completed: list[bytes] = []

        while len(self._pcm_pending) >= self._window_bytes:
            window_bytes = bytes(self._pcm_pending[: self._window_bytes])
            del self._pcm_pending[: self._window_bytes]

            floats = (
                np.frombuffer(window_bytes, dtype=np.int16).astype(np.float32)
                / 32768.0
            )
            speech_dict = self._iterator(floats, return_seconds=True)

            if speech_dict:
                if "start" in speech_dict:
                    self._collecting = True
                    self._segment_pcm = bytearray()
                if self._collecting:
                    self._segment_pcm.extend(window_bytes)
                if "end" in speech_dict and self._collecting:
                    if self._segment_pcm:
                        completed.append(bytes(self._segment_pcm))
                    self._collecting = False
                    self._segment_pcm = bytearray()
            elif self._collecting:
                self._segment_pcm.extend(window_bytes)

        return completed

    def flush(self) -> bytes | None:
        try:
            return self._flush_impl()
        except AppError:
            raise
        except Exception as exc:
            raise ProviderError("VAD 收尾失败", provider="silero-vad") from exc

    def _flush_impl(self) -> bytes | None:
        if self._collecting and self._segment_pcm:
            data = bytes(self._segment_pcm)
            self._collecting = False
            self._segment_pcm = bytearray()
            return data
        if self._pcm_pending:
            data = bytes(self._pcm_pending)
            self._pcm_pending.clear()
            if len(data) >= self._window_bytes // 2:
                return data
        # 预录音频/短句：VAD 未切出 end 时，用整段音频兜底
        if len(self._all_pcm) >= 3200:
            data = bytes(self._all_pcm)
            self._all_pcm.clear()
            return data
        return None

    def reset(self) -> None:
        self._pcm_pending.clear()
        self._segment_pcm.clear()
        self._all_pcm.clear()
        self._collecting = False
        if self._iterator is not None:
            self._iterator.reset_states()


@lru_cache
def get_vad_provider() -> BaseVAD:
    return SileroVADProvider()
