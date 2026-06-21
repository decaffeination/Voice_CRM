"""Voice Pipeline 集成测试（mock ASR/Agent/TTS）。"""

from __future__ import annotations

import pytest

from main_server.memory.memory_schema import ActorContext
from main_server.services.pipeline.voice_pipeline import voice_pipeline


@pytest.fixture
def actor(memory_db) -> ActorContext:
    return ActorContext(
        user_id=1,
        username="admin",
        roles=["Admin"],
        session_id="voice-pipeline-session",
        channel="voice",
    )


class TestVoicePipeline:
    @pytest.mark.asyncio
    async def test_run_from_file(
        self, actor: ActorContext, tmp_path, mock_agent_invoke, mock_asr, mock_tts
    ) -> None:
        # 场景：文件语音链路；输入：wav 路径；预期：transcript + reply + audio
        mock_agent_invoke("语音 Pipeline 回复")
        wav = tmp_path / "input.wav"
        wav.write_bytes(b"fake-wav-content")
        result = await voice_pipeline.run_from_file(
            str(wav), actor=actor, with_audio=True
        )
        assert result.transcript == "你好，这是测试语音"
        assert result.text == "语音 Pipeline 回复"
        assert result.audio_bytes == b"fake-audio-bytes"

    @pytest.mark.asyncio
    async def test_run_from_file_without_audio(
        self, actor: ActorContext, tmp_path, mock_agent_invoke, mock_asr, mock_tts
    ) -> None:
        mock_agent_invoke("语音 Pipeline 回复")
        wav = tmp_path / "input.wav"
        wav.write_bytes(b"fake-wav-content")
        result = await voice_pipeline.run_from_file(
            str(wav), actor=actor, with_audio=False
        )
        assert result.transcript == "你好，这是测试语音"
        assert result.text == "语音 Pipeline 回复"
        assert result.audio_bytes is None
