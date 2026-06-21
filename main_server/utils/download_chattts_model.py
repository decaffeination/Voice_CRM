from __future__ import annotations

from pathlib import Path

from main_server.config.settings import get_settings
from main_server.core.exceptions import ConfigError
from main_server.core.logger import logger

HF_REPO_ID = "2Noise/ChatTTS"
ASSET_DIR_NAME = "asset"
# 与 ChatTTS 官方 ChatTTS/utils/dl.py::check_all_assets 一致
REQUIRED_ASSET_PATHS = (
    "Decoder.safetensors",
    "DVAE.safetensors",
    "Embed.safetensors",
    "Vocos.safetensors",
    "gpt/config.json",
    "gpt/model.safetensors",
    "tokenizer/special_tokens_map.json",
    "tokenizer/tokenizer_config.json",
    "tokenizer/tokenizer.json",
)


def get_chattts_model_dir() -> Path:
    settings = get_settings()
    return settings.models.abs_tts_path


def get_chattts_asset_dir() -> Path:
    return get_chattts_model_dir() / ASSET_DIR_NAME


def _is_asset_file_ready(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _missing_asset_paths(asset_dir: Path) -> list[str]:
    return [
        rel_path
        for rel_path in REQUIRED_ASSET_PATHS
        if not _is_asset_file_ready(asset_dir / rel_path)
    ]


def _is_model_ready(model_dir: Path) -> bool:
    asset_dir = model_dir / ASSET_DIR_NAME
    if not asset_dir.is_dir():
        return False
    return not _missing_asset_paths(asset_dir)


def _download_from_huggingface(target_dir: Path) -> None:
    from huggingface_hub import hf_hub_download, snapshot_download

    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "从 HuggingFace 下载 ChatTTS 模型: %s -> %s",
        HF_REPO_ID,
        target_dir,
    )

    snapshot_download(
        repo_id=HF_REPO_ID,
        local_dir=str(target_dir),
        allow_patterns=[f"{ASSET_DIR_NAME}/**"],
        local_dir_use_symlinks=False,
        resume_download=True,
    )

    asset_dir = target_dir / ASSET_DIR_NAME
    missing = _missing_asset_paths(asset_dir)
    if not missing:
        return

    logger.info("snapshot 后仍缺 %d 个文件，尝试逐文件下载", len(missing))
    for rel_path in missing:
        hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=f"{ASSET_DIR_NAME}/{rel_path}",
            local_dir=str(target_dir),
            local_dir_use_symlinks=False,
            resume_download=True,
        )


def ensure_chattts_model_local() -> Path:
    """确保 ChatTTS 权重已下载到 data/models/chattts/asset。"""
    target_dir = get_chattts_model_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    if _is_model_ready(target_dir):
        logger.info("ChatTTS 模型已存在: %s", get_chattts_asset_dir())
        return target_dir

    try:
        _download_from_huggingface(target_dir)
    except Exception as exc:
        raise ConfigError(
            "ChatTTS 模型不可用。\n"
            f"目标目录: {target_dir}\n"
            "请执行: python -m main_server.utils.download_chattts_model\n"
            "或安装依赖: pip install huggingface_hub ChatTTS\n"
            "大文件下载较慢时可设置 HF_TOKEN 或 HF_HUB_ENABLE_HF_TRANSFER=1\n"
            f"详情: {exc}"
        ) from exc

    missing = _missing_asset_paths(get_chattts_asset_dir())
    if missing:
        raise ConfigError(
            "ChatTTS 模型下载完成但缺少权重文件。\n"
            f"目标目录: {get_chattts_asset_dir()}\n"
            f"缺少: {', '.join(missing)}\n"
            "建议删除不完整目录后重试，或设置 HF_TOKEN 加速大文件下载。"
        )

    logger.info("ChatTTS 模型已保存到 %s", get_chattts_asset_dir())
    return target_dir


def download_chattts_model() -> Path:
    """下载并返回 ChatTTS 模型根目录（含 asset/）。"""
    return ensure_chattts_model_local()


if __name__ == "__main__":
    model_dir = download_chattts_model()
    print(f"ChatTTS 模型就绪: {model_dir}")
    print(f"权重目录: {get_chattts_asset_dir()}")
