"""live 脚本用测试音频：使用仓库内固定样例，不自动生成。

请将清晰、完整的人声录音放到：

  tests/fixtures/recording.wav

也可通过各脚本的 --audio 指定其他 wav/mp3 文件。
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures"
FIXTURE_SAMPLE = FIXTURE_DIR / "recording.wav"

_SUPPORTED_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}


def _is_valid_audio(path: Path, *, min_bytes: int = 44) -> bool:
    return (
        path.is_file()
        and path.stat().st_size >= min_bytes
        and path.suffix.lower() in _SUPPORTED_SUFFIXES
    )


def ensure_audio(path: Path | None = None) -> Path:
    """返回可用于上传/WS 的音频路径。

    优先级：
    1. ``path`` 已存在且有效（含 ``--audio`` 传入）
    2. 固定样例 ``tests/fixtures/recording.wav``
    """
    if path is not None and _is_valid_audio(path):
        return path

    if _is_valid_audio(FIXTURE_SAMPLE):
        if path is None or path.resolve() != FIXTURE_SAMPLE.resolve():
            print(f"使用固定样例: {FIXTURE_SAMPLE}")
        return FIXTURE_SAMPLE

    raise FileNotFoundError(
        "未找到测试音频。\n"
        f"  请将清晰完整的人声录音放到: {FIXTURE_SAMPLE}\n"
        "  或在运行脚本时用 --audio 指定本地 wav/mp3 文件。"
    )
