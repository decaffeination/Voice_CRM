from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseASR(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str | Path) -> str:
        """将音频文件转写为文本。"""
