"""ChatTTS 模型下载工具测试。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from main_server.utils import download_chattts_model as downloader


@pytest.fixture
def chattts_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    model_dir = tmp_path / "chattts"
    asset_dir = model_dir / "asset"
    asset_dir.mkdir(parents=True)
    for name in downloader.REQUIRED_ASSET_FILES:
        (asset_dir / name).write_bytes(b"weights")
    monkeypatch.setattr(downloader, "get_chattts_model_dir", lambda: model_dir)
    return model_dir


class TestDownloadChatTTSModel:
    def test_ensure_skips_download_when_ready(self, chattts_dir: Path) -> None:
        with patch.object(downloader, "_download_from_huggingface") as mock_download:
            path = downloader.ensure_chattts_model_local()
        assert path == chattts_dir
        mock_download.assert_not_called()

    def test_ensure_downloads_when_missing(self, tmp_path: Path, monkeypatch) -> None:
        model_dir = tmp_path / "chattts"
        monkeypatch.setattr(downloader, "get_chattts_model_dir", lambda: model_dir)

        def _fake_download(target: Path) -> None:
            asset_dir = target / "asset"
            asset_dir.mkdir(parents=True, exist_ok=True)
            for name in downloader.REQUIRED_ASSET_FILES:
                (asset_dir / name).write_bytes(b"weights")

        with patch.object(
            downloader,
            "_download_from_huggingface",
            side_effect=_fake_download,
        ):
            path = downloader.ensure_chattts_model_local()

        assert path == model_dir
        assert downloader._is_model_ready(model_dir)
