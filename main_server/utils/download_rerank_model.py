from __future__ import annotations

from pathlib import Path

from main_server.config.settings import get_settings
from main_server.core.exceptions import ConfigError
from main_server.core.logger import logger
from main_server.utils.hf_model_loader import find_hf_snapshot, load_cross_encoder


def get_rerank_cache_dir() -> Path:
    return get_settings().models.abs_rerank_cache


def _is_model_ready(cache_dir: Path, model_id: str) -> bool:
    return find_hf_snapshot(cache_dir, model_id) is not None


def ensure_rerank_model_local() -> Path:
    """确保 Rerank 模型已缓存到 data/models/rerank。"""
    settings = get_settings()
    cache_dir = get_rerank_cache_dir()
    model_id = settings.models.rerank.model
    cache_dir.mkdir(parents=True, exist_ok=True)

    snapshot = find_hf_snapshot(cache_dir, model_id)
    if snapshot is not None:
        logger.info("Rerank 模型已存在: %s", snapshot)
        return snapshot

    logger.info("Rerank 模型未缓存，开始下载: %s -> %s", model_id, cache_dir)
    try:
        load_cross_encoder(model_id, cache_dir)
    except Exception as exc:
        raise ConfigError(
            f"Rerank 模型不可用: {model_id}\n"
            f"目标目录: {cache_dir}\n"
            f"请执行: python -m main_server.utils.download_rerank_model\n"
            f"详情: {exc}"
        ) from exc

    snapshot = find_hf_snapshot(cache_dir, model_id)
    if snapshot is None:
        raise ConfigError(
            f"Rerank 模型下载完成但未找到权重: {model_id}\n"
            f"目标目录: {cache_dir}"
        )
    logger.info("Rerank 模型已保存到 %s", snapshot)
    return snapshot


def download_rerank_model() -> Path:
    return ensure_rerank_model_local()


if __name__ == "__main__":
    path = download_rerank_model()
    print(f"Rerank 模型就绪: {path}")
