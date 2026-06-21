from __future__ import annotations

import asyncio
import base64
import binascii
import uuid
from pathlib import Path
from typing import Any

from main_server.core.exceptions import AppError, PipelineError, ValidationError
from main_server.core.provider_timeouts import resolve_provider_timeout
from main_server.core.pipeline_boundary import pipeline_stage
from main_server.core.ws_errors import send_ws_error
from main_server.memory.memory_schema import ActorContext
from main_server.providers.VAD.base import BaseVAD
from main_server.providers.VAD.silero import SileroVADProvider
from main_server.services.pipeline.chat_pipeline import ChatPipeline, chat_pipeline
from main_server.services.pipeline.stream_emitter import AsyncWsStreamEmitter
from main_server.services.voice_services.asr_service import transcribe
from main_server.utils.audio_utils import TEMP_AUDIO_DIR, cleanup_file, pcm_to_wav

# 16kHz mono int16：约 0.2s
_MIN_PCM_BYTES = 3200
# 建议最短有效语音约 0.5s
_MIN_UTTERANCE_BYTES = 8000


class RealtimePipeline:
    """WS 实时语音：Silero VAD 切分 → ASR → Chat Pipeline（流式文本 + 分句 TTS）。"""

    def __init__(
        self,
        actor: ActorContext,
        chat: ChatPipeline | None = None,
        vad: BaseVAD | None = None,
    ) -> None:
        self._actor = actor
        self._chat = chat or chat_pipeline
        # 每连接独立 VAD 状态，避免多会话串流
        self._vad = vad or SileroVADProvider()
        self._processing = False
        self._queued_segments: list[tuple[bytes, bool]] = []

    @property
    def session_id(self) -> str:
        return self._actor.session_id

    def reset_state(self) -> None:
        """连接断开或会话重置时清理 VAD 与排队状态。"""
        self._vad.reset()
        self._queued_segments.clear()

    async def send(self, websocket: Any, msg_type: str, **payload) -> None:
        await websocket.send_json({"type": msg_type, **payload})

    async def handle(self, message: dict, websocket: Any) -> None:
        msg_type = message.get("type", "")

        if msg_type == "ping":
            await self.send(websocket, "pong")
            return

        if msg_type == "audio":
            data_b64 = message.get("data", "")
            if not data_b64:
                return
            try:
                pcm_bytes = base64.b64decode(data_b64, validate=True)
            except (binascii.Error, ValueError):
                await send_ws_error(
                    websocket,
                    ValidationError("音频数据格式无效"),
                    stage="decode",
                )
                return
            try:
                completed = self._vad.feed(pcm_bytes)
            except AppError as exc:
                await send_ws_error(websocket, exc, stage="vad")
                return
            with_tts = bool(message.get("with_tts", True))
            for segment in completed:
                await self._submit_segment(segment, websocket, with_tts=with_tts)
            return

        if msg_type == "end":
            with_tts = bool(message.get("with_tts", True))
            try:
                tail = self._vad.flush()
            except AppError as exc:
                await send_ws_error(websocket, exc, stage="vad")
                return
            if tail:
                await self._submit_segment(tail, websocket, with_tts=with_tts)
            elif not self._processing and not self._queued_segments:
                await send_ws_error(
                    websocket,
                    ValidationError("未检测到有效语音，请按住说话后再松手"),
                    stage="vad",
                )
            return

        if msg_type == "reset":
            self.reset_state()
            await self.send(websocket, "reset_ok")
            return

        await send_ws_error(
            websocket,
            ValidationError(f"未知消息类型: {msg_type}"),
            stage="handle",
        )

    async def _submit_segment(
        self, pcm_bytes: bytes, websocket: Any, *, with_tts: bool
    ) -> None:
        if self._processing:
            self._queued_segments.append((pcm_bytes, with_tts))
            return
        await self._process_segment(pcm_bytes, websocket, with_tts=with_tts)

    def _transcribe(self, wav_path: Path) -> str:
        with pipeline_stage("asr", session_id=self.session_id):
            return transcribe(wav_path)

    async def _process_segment(
        self, pcm_bytes: bytes, websocket: Any, *, with_tts: bool = True
    ) -> None:
        if len(pcm_bytes) < _MIN_PCM_BYTES:
            await send_ws_error(
                websocket,
                ValidationError("录音太短，请按住说话至少 0.2 秒"),
                stage="vad",
            )
            return
        if len(pcm_bytes) < _MIN_UTTERANCE_BYTES:
            await send_ws_error(
                websocket,
                ValidationError("录音太短，请按住说话至少 0.5 秒"),
                stage="vad",
            )
            return

        self._processing = True
        try:
            timeout = resolve_provider_timeout("pipeline")
            await asyncio.wait_for(
                self._process_segment_inner(
                    pcm_bytes, websocket, with_tts=with_tts
                ),
                timeout=timeout,
            )
        except TimeoutError:
            await send_ws_error(
                websocket,
                PipelineError("语音处理超时", stage="process_segment"),
                stage="process_segment",
            )
        finally:
            self._processing = False
            if self._queued_segments:
                pcm, with_tts = self._queued_segments.pop(0)
                await self._process_segment(
                    pcm, websocket, with_tts=with_tts
                )

    async def _process_segment_inner(
        self, pcm_bytes: bytes, websocket: Any, *, with_tts: bool = True
    ) -> None:
        wav_path: Path | None = None
        try:
            with pipeline_stage("vad_encode", session_id=self.session_id):
                TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
                wav_path = TEMP_AUDIO_DIR / f"ws_{uuid.uuid4().hex}.wav"
                pcm_to_wav(pcm_bytes, wav_path)

            transcript = await asyncio.to_thread(self._transcribe, wav_path)
            await self.send(websocket, "asr_final", text=transcript)

            loop = asyncio.get_running_loop()
            emitter = AsyncWsStreamEmitter(loop, self.send, websocket)

            result = await self._chat.run_stream_async(
                actor=self._actor,
                user_input=transcript,
                emitter=emitter,
                with_tts=with_tts,
            )
            if result.session_title:
                await self.send(
                    websocket,
                    "session_title",
                    title=result.session_title,
                )
        except AppError as exc:
            await send_ws_error(websocket, exc, stage="process_segment")
        except Exception as exc:
            await send_ws_error(websocket, exc, stage="process_segment")
        finally:
            if wav_path is not None:
                cleanup_file(wav_path)
