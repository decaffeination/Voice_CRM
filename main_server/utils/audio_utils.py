from __future__ import annotations

import uuid
from pathlib import Path

from main_server.config.settings import PROJECT_ROOT
from main_server.core.exceptions import ValidationError

SUPPORTED_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}
TEMP_AUDIO_DIR = PROJECT_ROOT / "main_server" / "data" / "temp_audio"


def ensure_audio_file(audio_path: str | Path) -> Path:
    path = Path(audio_path)
    if not path.exists():
        raise ValidationError(f"音频文件不存在: {path}")
    if path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
        raise ValidationError(
            f"不支持的音频格式: {path.suffix}，支持 {', '.join(sorted(SUPPORTED_AUDIO_SUFFIXES))}"
        )
    return path


def save_upload_bytes(data: bytes, suffix: str) -> Path:
    if not data:
        raise ValidationError("音频文件为空")
    ext = suffix.lower() if suffix.startswith(".") else f".{suffix.lower()}"
    if ext not in SUPPORTED_AUDIO_SUFFIXES:
        raise ValidationError(f"不支持的音频格式: {ext}")

    TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    file_path = TEMP_AUDIO_DIR / f"{uuid.uuid4().hex}{ext}"
    file_path.write_bytes(data)
    return file_path


def cleanup_file(path: str | Path) -> None:
    file_path = Path(path)
    if file_path.exists():
        file_path.unlink(missing_ok=True)


def pcm_to_wav(
    pcm_bytes: bytes,
    wav_path: str | Path,
    sample_rate: int = 16000,
) -> Path:
    """将 16-bit mono PCM 写入 WAV 文件。"""
    import wave

    path = Path(wav_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return path
