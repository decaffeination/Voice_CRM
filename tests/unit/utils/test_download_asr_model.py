"""ASR 模型下载工具测试。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from main_server.utils import download_asr_model as downloader


@pytest.fixture
def asr_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    model_dir = tmp_path / "SenseVoiceSmall"
    model_dir.mkdir(parents=True)
    (model_dir / downloader.WEIGHTS_FILE).write_bytes(b"weights")
    monkeypatch.setattr(downloader, "get_asr_model_dir", lambda: model_dir)
    return model_dir


class TestDownloadASRModel:
    def test_ensure_skips_download_when_ready(self, asr_dir: Path) -> None:
        with (
            patch.object(downloader, "_download_from_modelscope") as mock_ms,
            patch.object(downloader, "_download_from_huggingface") as mock_hf,
        ):
            path = downloader.ensure_asr_model_local()
        assert path == asr_dir / downloader.WEIGHTS_FILE
        mock_ms.assert_not_called()
        mock_hf.assert_not_called()

    def test_ensure_downloads_when_missing(self, tmp_path: Path, monkeypatch) -> None:
        model_dir = tmp_path / "SenseVoiceSmall"
        monkeypatch.setattr(downloader, "get_asr_model_dir", lambda: model_dir)

        def _fake_ms(target: Path) -> None:
            target.mkdir(parents=True, exist_ok=True)
            (target / downloader.WEIGHTS_FILE).write_bytes(b"weights")

        with patch.object(
            downloader,
            "_download_from_modelscope",
            side_effect=_fake_ms,
        ):
            path = downloader.ensure_asr_model_local()

        assert path == model_dir / downloader.WEIGHTS_FILE
        assert downloader._is_model_ready(model_dir)
