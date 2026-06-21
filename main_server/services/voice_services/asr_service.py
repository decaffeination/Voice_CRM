from __future__ import annotations

from pathlib import Path

from main_server.core.exceptions import ValidationError
from main_server.providers import bootstrap as _providers_bootstrap  # noqa: F401
from main_server.providers.registry import get_asr_provider
from main_server.utils.audio_utils import ensure_audio_file


def transcribe(audio_path: str | Path) -> str:
    path = ensure_audio_file(audio_path)
    text = get_asr_provider().transcribe(path)
    if not text:
        raise ValidationError("未能识别出语音内容，请重新录制")
    return text
