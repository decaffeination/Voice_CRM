from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar

from main_server.core.logger import logger

T = TypeVar("T")

_WEIGHT_FILENAMES = (
    "model.safetensors",
    "pytorch_model.bin",
    "model.pt",
)


def model_id_to_cache_dirname(model_id: str) -> str:
    return "models--" + model_id.replace("/", "--")


def find_hf_snapshot(cache_dir: Path, model_id: str) -> Path | None:
    """在 HuggingFace 风格缓存目录中查找含权重的最新 snapshot。"""
    snapshots_root = cache_dir / model_id_to_cache_dirname(model_id) / "snapshots"
    if not snapshots_root.is_dir():
        return None

    candidates = sorted(
        (path for path in snapshots_root.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for snapshot in candidates:
        if snapshot_has_weights(snapshot):
            return snapshot
    return None


def snapshot_has_weights(snapshot: Path) -> bool:
    for name in _WEIGHT_FILENAMES:
        candidate = snapshot / name
        if candidate.is_file() and candidate.stat().st_size > 0:
            return True
    for pattern in ("*.safetensors", "*.bin", "*.pt"):
        for candidate in snapshot.glob(pattern):
            if candidate.is_file() and candidate.stat().st_size > 0:
                return True
    return False


def load_hf_model(
    *,
    model_name: str,
    cache_folder: str | Path,
    label: str,
    factory: Callable[..., T],
    **factory_kwargs,
) -> T:
    """有本地缓存则离线加载，失败再联网。"""
    cache_dir = Path(cache_folder)
    cache_dir.mkdir(parents=True, exist_ok=True)

    snapshot = find_hf_snapshot(cache_dir, model_name)
    if snapshot is not None:
        try:
            logger.info("离线加载 %s: %s (snapshot=%s)", label, model_name, snapshot)
            return factory(str(snapshot), local_files_only=True, **factory_kwargs)
        except Exception as exc:
            logger.warning("离线 snapshot 加载 %s 失败: %s", label, exc)

    try:
        logger.info("离线加载 %s: %s, cache=%s", label, model_name, cache_dir)
        return factory(
            model_name,
            cache_folder=str(cache_dir),
            local_files_only=True,
            **factory_kwargs,
        )
    except Exception as exc:
        logger.warning("离线加载 %s 失败，改为联网: %s", label, exc)

    logger.info("联网加载 %s: %s, cache=%s", label, model_name, cache_dir)
    return factory(model_name, cache_folder=str(cache_dir), **factory_kwargs)


def load_sentence_transformer(model_name: str, cache_folder: str | Path):
    from sentence_transformers import SentenceTransformer

    return load_hf_model(
        model_name=model_name,
        cache_folder=cache_folder,
        label="Embedding 模型",
        factory=SentenceTransformer,
    )


def load_cross_encoder(model_name: str, cache_folder: str | Path):
    from sentence_transformers import CrossEncoder

    return load_hf_model(
        model_name=model_name,
        cache_folder=cache_folder,
        label="Rerank 模型",
        factory=CrossEncoder,
    )
