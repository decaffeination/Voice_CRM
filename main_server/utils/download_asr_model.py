from __future__ import annotations

from pathlib import Path

from main_server.config.settings import get_settings
from main_server.core.exceptions import ConfigError
from main_server.core.logger import logger

# 与 main_server/data/models/SenseVoiceSmall/configuration.json 保持一致
MS_MODEL_ID = "iic/SenseVoiceSmall"
HF_MODEL_ID = "FunAudioLLM/SenseVoiceSmall"
WEIGHTS_FILE = "model.pt"


def get_asr_model_dir() -> Path:
    settings = get_settings()
    return settings.models.abs_asr_path


def get_asr_model_path() -> Path:
    return get_asr_model_dir() / WEIGHTS_FILE


def _is_model_ready(model_dir: Path) -> bool:
    weights = model_dir / WEIGHTS_FILE
    return weights.is_file() and weights.stat().st_size > 0


def _download_from_modelscope(target_dir: Path) -> None:
    from modelscope.hub.snapshot_download import snapshot_download

    logger.info("从 ModelScope 下载 ASR 模型: %s -> %s", MS_MODEL_ID, target_dir)
    snapshot_download(
        MS_MODEL_ID,
        local_dir=str(target_dir),
        revision="master",
    )


def _download_from_huggingface(target_dir: Path) -> None:
    from huggingface_hub import snapshot_download

    try:
        logger.info(
            "尝试从 HuggingFace 本地缓存恢复 ASR 模型: %s -> %s",
            HF_MODEL_ID,
            target_dir,
        )
        snapshot_download(
            repo_id=HF_MODEL_ID,
            local_dir=str(target_dir),
            local_files_only=True,
        )
        if _is_model_ready(target_dir):
            return
    except Exception as exc:
        logger.warning("HuggingFace 离线缓存不可用，改为联网下载: %s", exc)

    logger.info("从 HuggingFace 下载 ASR 模型: %s -> %s", HF_MODEL_ID, target_dir)
    snapshot_download(
        repo_id=HF_MODEL_ID,
        local_dir=str(target_dir),
    )


def ensure_asr_model_local() -> Path:
    """确保 SenseVoiceSmall 已下载到 data/models/SenseVoiceSmall（含 model.pt）。"""
    target_dir = get_asr_model_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    if _is_model_ready(target_dir):
        path = target_dir / WEIGHTS_FILE
        logger.info("ASR 模型已存在: %s", path)
        return path

    errors: list[str] = []
    modelscope_ok = False

    try:
        _download_from_modelscope(target_dir)
        modelscope_ok = True
    except Exception as exc:
        errors.append(f"ModelScope: {exc}")
        logger.warning("ModelScope 下载失败，尝试 HuggingFace: %s", exc)

    if modelscope_ok and _is_model_ready(target_dir):
        path = target_dir / WEIGHTS_FILE
        logger.info("ASR 模型已保存到 %s", path)
        return path

    if modelscope_ok:
        errors.append("ModelScope 下载完成但未找到 model.pt")

    try:
        _download_from_huggingface(target_dir)
    except Exception as exc:
        errors.append(f"HuggingFace: {exc}")
    else:
        if _is_model_ready(target_dir):
            path = target_dir / WEIGHTS_FILE
            logger.info("ASR 模型已保存到 %s", path)
            return path
        errors.append("HuggingFace 下载完成但未找到 model.pt")

    detail = "\n".join(errors)
    raise ConfigError(
        f"SenseVoiceSmall 模型不可用（缺少 {WEIGHTS_FILE}）。\n"
        f"目标目录: {target_dir}\n"
        f"请执行: python -m main_server.utils.download_asr_model\n"
        f"或安装依赖: pip install modelscope huggingface_hub\n"
        f"详情:\n{detail}"
    )


def download_asr_model() -> Path:
    """下载并返回 model.pt 路径。"""
    return ensure_asr_model_local()


if __name__ == "__main__":
    model_path = download_asr_model()
    model_dir = model_path.parent
    print(f"ASR 模型就绪: {model_dir}")
    print(f"权重文件: {model_path}")
