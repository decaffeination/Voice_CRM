from __future__ import annotations

import shutil
from pathlib import Path

from main_server.config.settings import get_settings
from main_server.core.exceptions import ConfigError
from main_server.core.logger import logger

VAD_JIT_NAME = "silero_vad.jit"
VAD_ONNX_NAME = "silero_vad_op18_ifless.onnx"
VAD_ONNX_URL = (
    "https://github.com/snakers4/silero-vad/raw/master/"
    "src/silero_vad/data/silero_vad_op18_ifless.onnx"
)


def get_vad_model_path() -> Path:
    settings = get_settings()
    return settings.models.abs_vad_path / VAD_ONNX_NAME


def _download_file(url: str, target: Path) -> None:
    import urllib.request

    logger.info("下载 VAD 模型: %s", url)
    with urllib.request.urlopen(url, timeout=120) as resp:
        target.write_bytes(resp.read())


def _copy_packaged_onnx(target_file: Path) -> bool:
    try:
        from importlib import resources

        package = resources.files("silero_vad.data")
        source = package.joinpath(VAD_ONNX_NAME)
        with resources.as_file(source) as src_path:
            shutil.copy2(src_path, target_file)
        return True
    except Exception:
        return False


def ensure_vad_model_local() -> Path:
    """确保本地存在 Silero VAD ONNX 模型。"""
    settings = get_settings()
    target_dir = settings.models.abs_vad_path
    target_file = target_dir / VAD_ONNX_NAME
    target_dir.mkdir(parents=True, exist_ok=True)

    if target_file.exists():
        return target_file

    if _copy_packaged_onnx(target_file):
        logger.info("VAD 模型已从 silero-vad 包复制到 %s", target_file)
        return target_file

    try:
        _download_file(VAD_ONNX_URL, target_file)
    except Exception as exc:
        raise ConfigError(
            "Silero VAD 模型不可用。请执行: pip install silero-vad\n"
            f"或手动下载到 {target_file}"
        ) from exc

    logger.info("VAD 模型已保存到 %s", target_file)
    return target_file


def download_vad_model() -> Path:
    return ensure_vad_model_local()


if __name__ == "__main__":
    path = download_vad_model()
    print(f"VAD 模型就绪: {path}")
