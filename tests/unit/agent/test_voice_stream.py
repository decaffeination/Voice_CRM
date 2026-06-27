"""流式语音与分句 TTS 单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from main_server.core.stream_context import reset_stream_emitter, set_stream_emitter
from main_server.services.pipeline.stream_emitter import AsyncWsStreamEmitter
from main_server.utils.text_split import split_sentences


class TestSplitSentences:
    def test_chinese_sentences(self) -> None:
        text = "你好。这是第二句！还有第三句？"
        parts = split_sentences(text)
        assert len(parts) >= 3
        assert "你好" in parts[0]

    def test_single_sentence(self) -> None:
        assert split_sentences("单句回复") == ["单句回复"]

    def test_empty(self) -> None:
        assert split_sentences("   ") == []


class TestAsyncWsStreamEmitter:
    @pytest.mark.asyncio
    async def test_schedules_messages(self) -> None:
        sent: list[tuple[str, dict]] = []

        async def send(_ws, msg_type: str, **payload):
            sent.append((msg_type, payload))

        loop = __import__("asyncio").get_running_loop()
        emitter = AsyncWsStreamEmitter(loop, send, websocket=object())

        emitter.on_text_delta("你")
        emitter.on_text_delta("好")
        emitter.on_text_final("你好", intent="chitchat")
        emitter.on_tts_chunk(0, "你好。", "YQ==")
        emitter.on_tts_done(1)

        await __import__("asyncio").sleep(0.05)

        types = [item[0] for item in sent]
        assert types.count("agent_text_delta") == 2
        assert "agent_text" in types
        assert "tts_audio_chunk" in types
        assert "tts_done" in types


class TestResponseNodeStreaming:
    def test_template_emits_final(self) -> None:
        from agent.nodes.response_node import response_node

        emitter = MagicMock()
        token = set_stream_emitter(emitter)
        try:
            result = response_node(
                {
                    "tool_result": {"cancelled": True},
                    "conversation_state": {},
                }
            )
        finally:
            reset_stream_emitter(token)

        assert "已取消" in result["final_response"]
        emitter.on_text_final.assert_called_once()

    @patch("agent.nodes.response_node.llm_service.chat_stream")
    def test_llm_stream_emits_deltas(self, mock_stream: MagicMock) -> None:
        from agent.nodes.response_node import response_node

        mock_stream.return_value = iter(["回", "复"])
        emitter = MagicMock()
        token = set_stream_emitter(emitter)
        try:
            result = response_node(
                {
                    "user_input": "你好",
                    "tool_results": [],
                    "conversation_state": {},
                }
            )
        finally:
            reset_stream_emitter(token)

        assert result["final_response"] == "回复"
        assert emitter.on_text_delta.call_count == 2
        emitter.on_text_final.assert_called_once_with("回复", intent=None, citations=None)
