from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from agent.state import ConversationState
from main_server.core.exceptions import PipelineError
from main_server.core.provider_timeouts import resolve_provider_timeout
from main_server.core.pipeline_boundary import pipeline_stage
from main_server.memory.memory_schema import ActorContext
from main_server.services.pipeline.chat_pipeline import ChatPipeline, chat_pipeline
from main_server.services.voice_services.asr_service import transcribe


@dataclass
class VoicePipelineResult:
    transcript: str
    text: str
    audio_bytes: bytes | None
    conversation_state: ConversationState
    intent: str | None = None
    session_title: str | None = None


class VoicePipeline:
    """上传音频：ASR → Chat Pipeline → 可选 TTS。"""

    def __init__(self, chat: ChatPipeline | None = None) -> None:
        self._chat = chat or chat_pipeline

    def _transcribe(self, audio_path: str | Path, *, session_id: str) -> str:
        with pipeline_stage("asr", session_id=session_id):
            return transcribe(audio_path)

    async def run_from_file(
        self,
        audio_path: str | Path,
        *,
        actor: ActorContext,
        with_audio: bool = False,
    ) -> VoicePipelineResult:
        timeout = resolve_provider_timeout("pipeline")
        try:
            return await asyncio.wait_for(
                self._run_from_file_inner(
                    audio_path, actor=actor, with_audio=with_audio
                ),
                timeout=timeout,
            )
        except TimeoutError as exc:
            raise PipelineError("语音处理超时", stage="voice_pipeline") from exc

    async def _run_from_file_inner(
        self,
        audio_path: str | Path,
        *,
        actor: ActorContext,
        with_audio: bool,
    ) -> VoicePipelineResult:
        transcript = await asyncio.to_thread(
            self._transcribe, audio_path, session_id=actor.session_id
        )
        chat_result = await self._chat.run_async(
            actor=actor,
            user_input=transcript,
            with_audio=with_audio,
        )
        return VoicePipelineResult(
            transcript=transcript,
            text=chat_result.text,
            audio_bytes=chat_result.audio_bytes,
            conversation_state=chat_result.conversation_state,
            intent=chat_result.intent,
            session_title=chat_result.session_title,
        )


voice_pipeline = VoicePipeline()
