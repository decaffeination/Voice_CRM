"""Chat Pipeline 集成测试（mock Agent/TTS）。"""

from __future__ import annotations

import pytest

from main_server.memory.memory_schema import ActorContext
from main_server.services.pipeline.chat_pipeline import chat_pipeline


@pytest.fixture
def actor(memory_db) -> ActorContext:
    return ActorContext(
        user_id=1,
        username="admin",
        roles=["Admin"],
        session_id="test-session-pipeline",
        channel="text",
    )


class TestChatPipeline:
    @pytest.mark.asyncio
    async def test_run_async_text_only(
        self, actor: ActorContext, mock_agent_invoke
    ) -> None:
        # 场景：纯文本对话；输入：message；预期：reply 来自 mock
        mock_agent_invoke("Pipeline 测试回复")
        result = await chat_pipeline.run_async(
            actor=actor,
            user_input="你好",
            with_audio=False,
        )
        assert result.text == "Pipeline 测试回复"

    @pytest.mark.asyncio
    async def test_run_async_with_tts(
        self, actor: ActorContext, mock_agent_invoke, mock_tts
    ) -> None:
        # 场景：带 TTS；输入：with_audio=True；预期：audio_bytes 非空
        mock_agent_invoke("带语音的回复")
        result = await chat_pipeline.run_async(
            actor=actor,
            user_input="播放",
            with_audio=True,
        )
        assert result.audio_bytes == b"fake-audio-bytes"

    @pytest.mark.asyncio
    async def test_run_async_tts_failure_returns_text(
        self, actor: ActorContext, mock_agent_invoke, monkeypatch
    ) -> None:
        from unittest.mock import AsyncMock

        from main_server.core.exceptions import TTSConnectionError

        mock_agent_invoke("文字回复")
        mock_tts = AsyncMock(
            side_effect=TTSConnectionError(provider="edge-tts"),
        )
        monkeypatch.setattr(
            "main_server.services.pipeline.chat_pipeline.synthesize_async",
            mock_tts,
        )

        result = await chat_pipeline.run_async(
            actor=actor,
            user_input="播放",
            with_audio=True,
        )
        assert result.text == "文字回复"
        assert result.audio_bytes is None

    def test_run_sync(self, actor: ActorContext, mock_agent_invoke) -> None:
        # 场景：同步 run；输入：user_input；预期：text 正确
        mock_agent_invoke("同步回复")
        result = chat_pipeline.run(actor=actor, user_input="sync")
        assert result.text == "同步回复"
        assert result.audio_bytes is None

    @pytest.mark.asyncio
    async def test_agent_failure_raises_pipeline_error(
        self, actor: ActorContext, monkeypatch
    ) -> None:
        # 场景：Agent 异常；输入：invoke 抛 PipelineError；预期：透传 Agent 错误
        from main_server.core.exceptions import PipelineError

        def _fail(*, turn):
            raise PipelineError("Agent 处理失败", stage="agent_invoke")

        monkeypatch.setattr(
            "main_server.services.pipeline.chat_pipeline.agent_service.invoke",
            _fail,
        )

        with pytest.raises(PipelineError, match="Agent"):
            await chat_pipeline.run_async(actor=actor, user_input="fail")
