from __future__ import annotations

from abc import ABC, abstractmethod


class BaseVAD(ABC):
    @abstractmethod
    def feed(self, pcm_bytes: bytes) -> list[bytes]:
        """输入 PCM 片段，返回已完成的语音段（16-bit mono PCM）。"""

    @abstractmethod
    def flush(self) -> bytes | None:
        """刷新缓冲区，返回未结束的语音段（若有）。"""

    @abstractmethod
    def reset(self) -> None:
        """重置检测状态。"""
