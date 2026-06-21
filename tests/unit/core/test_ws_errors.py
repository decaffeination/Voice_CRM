"""WebSocket 错误协议与 realtime_pipeline 异常边界测试。"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from main_server.core.context import request_id_var
from main_server.core.exceptions import (
    InternalServerError,
    LLMError,
    PipelineError,
    ValidationError,
)
from main_server.core.ws_errors import build_ws_error_payload, send_ws_error
from main_server.services.pipeline.realtime_pipeline import RealtimePipeline


class FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send_json(self, data: dict[str, Any]) -> None:
        self.messages.append(data)


class FakeVAD:
    """测试用 VAD：feed 累积 PCM，flush 时一次性返回（模拟 Silero 短句兜底）。"""

    def __init__(self, min_flush_bytes: int = 3200) -> None:
        self._buffer = bytearray()
        self._min_flush_bytes = min_flush_bytes

    def feed(self, pcm_bytes: bytes) -> list[bytes]:
        self._buffer.extend(pcm_bytes)
        return []

    def flush(self) -> bytes | None:
        if len(self._buffer) >= self._min_flush_bytes:
            data = bytes(self._buffer)
            self._buffer.clear()
            return data
        self._buffer.clear()
        return None

    def reset(self) -> None:
        self._buffer.clear()


class TestWsErrorPayload:
    @pytest.fixture(autouse=True)
    def _set_request_id(self) -> None:
        self._token = request_id_var.set("ws-req-001")

    def teardown_method(self) -> None:
        request_id_var.reset(self._token)

    def test_app_error_payload(self) -> None:
        payload = build_ws_error_payload(
            ValidationError("参数错误"),
            stage="handle",
        )
        assert payload == {
            "type": "error",
            "request_id": "ws-req-001",
            "code": "VALIDATION_ERROR",
            "message": "参数错误",
            "stage": "handle",
        }

    def test_pipeline_error_includes_stage(self) -> None:
        payload = build_ws_error_payload(
            PipelineError("处理失败", stage="agent_invoke")
        )
        assert payload["type"] == "error"
        assert payload["code"] == "PIPELINE_ERROR"
        assert payload["stage"] == "agent_invoke"

    def test_provider_error_includes_provider(self) -> None:
        payload = build_ws_error_payload(
            LLMError("LLM 失败", provider="deepseek"),
            stage="tts",
        )
        assert payload["code"] == "LLM_ERROR"
        assert payload["provider"] == "deepseek"
        assert "stage" not in payload

    def test_unexpected_error_becomes_internal(self) -> None:
        payload = build_ws_error_payload(RuntimeError("boom"), stage="process")
        internal = InternalServerError()
        assert payload["code"] == internal.code
        assert payload["message"] == internal.message
        assert payload["stage"] == "process"

    def test_send_ws_error(self) -> None:
        ws = FakeWebSocket()
        asyncio.run(send_ws_error(ws, ValidationError("无效"), stage="decode"))
        assert len(ws.messages) == 1
        assert ws.messages[0]["type"] == "error"
        assert ws.messages[0]["code"] == "VALIDATION_ERROR"


class TestRealtimePipelineDecode:
    @pytest.fixture
    def fake_vad(self) -> FakeVAD:
        return FakeVAD()

    @pytest.fixture
    def pipeline(self, fake_vad: FakeVAD) -> RealtimePipeline:
        from main_server.memory.memory_schema import ActorContext

        actor = ActorContext(
            user_id=1,
            username="admin",
            roles=["Admin"],
            session_id="sess-ws-1",
            channel="voice",
        )
        return RealtimePipeline(actor=actor, vad=fake_vad)

    def test_invalid_base64_sends_ws_error(
        self, pipeline: RealtimePipeline
    ) -> None:
        ws = FakeWebSocket()
        asyncio.run(
            pipeline.handle({"type": "audio", "data": "!!!not-base64!!!"}, ws)
        )
        assert len(ws.messages) == 1
        err = ws.messages[0]
        assert err["type"] == "error"
        assert err["code"] == "VALIDATION_ERROR"
        assert err["message"] == "音频数据格式无效"
        assert err["stage"] == "decode"

    def test_unknown_message_type(self, pipeline: RealtimePipeline) -> None:
        ws = FakeWebSocket()
        asyncio.run(pipeline.handle({"type": "unknown"}, ws))
        assert ws.messages[0]["code"] == "VALIDATION_ERROR"
        assert ws.messages[0]["stage"] == "handle"

    def test_ping_pong(self, pipeline: RealtimePipeline) -> None:
        ws = FakeWebSocket()
        asyncio.run(pipeline.handle({"type": "ping"}, ws))
        assert ws.messages == [{"type": "pong"}]

    def test_reset_ok(self, pipeline: RealtimePipeline) -> None:
        # 场景：VAD reset；输入：type=reset；预期：reset_ok
        ws = FakeWebSocket()
        asyncio.run(pipeline.handle({"type": "reset"}, ws))
        assert ws.messages == [{"type": "reset_ok"}]

    def test_end_no_speech_sends_ws_error(
        self, pipeline: RealtimePipeline
    ) -> None:
        ws = FakeWebSocket()
        asyncio.run(pipeline.handle({"type": "end"}, ws))
        assert len(ws.messages) == 1
        err = ws.messages[0]
        assert err["type"] == "error"
        assert err["code"] == "VALIDATION_ERROR"
        assert err["stage"] == "vad"

    def test_short_segment_sends_ws_error(
        self, pipeline: RealtimePipeline
    ) -> None:
        ws = FakeWebSocket()
        asyncio.run(pipeline._process_segment(b"\x00" * 100, ws))
        assert len(ws.messages) == 1
        err = ws.messages[0]
        assert err["type"] == "error"
        assert err["code"] == "VALIDATION_ERROR"
        assert err["stage"] == "vad"

    def test_audio_accumulates_until_end(
        self, pipeline: RealtimePipeline, fake_vad: FakeVAD
    ) -> None:
        import base64

        ws = FakeWebSocket()
        chunk = base64.b64encode(b"\x00" * 4000).decode("ascii")
        asyncio.run(pipeline.handle({"type": "audio", "data": chunk}, ws))
        assert len(fake_vad._buffer) == 4000
        assert ws.messages == []

    def test_end_rejects_short_utterance(self, pipeline: RealtimePipeline) -> None:
        import base64

        ws = FakeWebSocket()
        chunk = base64.b64encode(b"\x00" * 4000).decode("ascii")
        asyncio.run(pipeline.handle({"type": "audio", "data": chunk}, ws))
        asyncio.run(pipeline.handle({"type": "end"}, ws))
        assert ws.messages[-1]["type"] == "error"
        assert ws.messages[-1]["stage"] == "vad"

    def test_reset_clears_accumulator(
        self, pipeline: RealtimePipeline, fake_vad: FakeVAD
    ) -> None:
        import base64

        ws = FakeWebSocket()
        chunk = base64.b64encode(b"\x00" * 1000).decode("ascii")
        asyncio.run(pipeline.handle({"type": "audio", "data": chunk}, ws))
        asyncio.run(pipeline.handle({"type": "reset"}, ws))
        assert ws.messages == [{"type": "reset_ok"}]
        assert len(fake_vad._buffer) == 0
