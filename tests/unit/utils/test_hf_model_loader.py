"""HuggingFace 模型离线优先加载工具。"""

from pathlib import Path

from main_server.utils.hf_model_loader import (
    find_hf_snapshot,
    model_id_to_cache_dirname,
    snapshot_has_weights,
)


def test_model_id_to_cache_dirname() -> None:
    assert model_id_to_cache_dirname("BAAI/bge-small-zh-v1.5") == (
        "models--BAAI--bge-small-zh-v1.5"
    )


def test_find_hf_snapshot_prefers_snapshot_with_weights(tmp_path: Path) -> None:
    model_id = "org/demo"
    snapshot = (
        tmp_path
        / model_id_to_cache_dirname(model_id)
        / "snapshots"
        / "abc123"
    )
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_text("{}", encoding="utf-8")

    empty_snapshot = (
        tmp_path
        / model_id_to_cache_dirname(model_id)
        / "snapshots"
        / "older"
    )
    empty_snapshot.mkdir(parents=True)

    assert find_hf_snapshot(tmp_path, model_id) is None

    (snapshot / "model.safetensors").write_bytes(b"x" * 16)
    assert find_hf_snapshot(tmp_path, model_id) == snapshot


def test_snapshot_has_weights(tmp_path: Path) -> None:
    snapshot = tmp_path / "snap"
    snapshot.mkdir()
    assert snapshot_has_weights(snapshot) is False

    (snapshot / "pytorch_model.bin").write_bytes(b"weight")
    assert snapshot_has_weights(snapshot) is True
