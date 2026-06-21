"""音频工具单元测试。"""

from __future__ import annotations

import pytest

from main_server.core.exceptions import ValidationError
from main_server.utils.audio_utils import (
    cleanup_file,
    ensure_audio_file,
    pcm_to_wav,
    save_upload_bytes,
)


class TestAudioUtils:
    def test_save_upload_bytes_success(self, tmp_path, monkeypatch) -> None:
        # 场景：保存上传音频；输入：wav 字节；预期：文件存在
        monkeypatch.setattr(
            "main_server.utils.audio_utils.TEMP_AUDIO_DIR", tmp_path
        )
        path = save_upload_bytes(b"fake-wav-data", ".wav")
        assert path.exists()
        assert path.suffix == ".wav"
        cleanup_file(path)

    def test_save_empty_raises(self) -> None:
        # 场景：空文件；输入：空 bytes；预期：ValidationError
        with pytest.raises(ValidationError, match="空"):
            save_upload_bytes(b"", ".wav")

    def test_save_unsupported_suffix_raises(self) -> None:
        # 场景：不支持格式；输入：.xyz；预期：ValidationError
        with pytest.raises(ValidationError, match="不支持"):
            save_upload_bytes(b"data", ".xyz")

    def test_ensure_audio_file_not_exists(self) -> None:
        # 场景：文件不存在；输入：无效路径；预期：ValidationError
        with pytest.raises(ValidationError, match="不存在"):
            ensure_audio_file("/nonexistent/file.wav")

    def test_ensure_audio_file_bad_suffix(self, tmp_path) -> None:
        # 场景：错误后缀；输入：.txt 文件；预期：ValidationError
        bad = tmp_path / "audio.txt"
        bad.write_text("not audio")
        with pytest.raises(ValidationError, match="不支持"):
            ensure_audio_file(bad)

    def test_pcm_to_wav(self, tmp_path) -> None:
        # 场景：PCM 转 WAV；输入：16-bit mono PCM；预期：有效 wav 文件
        wav_path = tmp_path / "out.wav"
        pcm_to_wav(b"\x00\x00\xff\xff", wav_path, sample_rate=16000)
        assert wav_path.exists()
        assert wav_path.stat().st_size > 0

    def test_cleanup_file(self, tmp_path) -> None:
        # 场景：清理临时文件；输入：存在文件；预期：删除后不存在
        f = tmp_path / "temp.wav"
        f.write_bytes(b"x")
        cleanup_file(f)
        assert not f.exists()
