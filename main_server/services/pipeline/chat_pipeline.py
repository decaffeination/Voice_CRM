from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from typing import Any

from agent.state import ConversationState
from main_server.core.context import session_id_var, user_id_var
from main_server.core.exceptions import ProviderError
from main_server.core.logger import logger
from main_server.core.pipeline_boundary import async_pipeline_stage, pipeline_stage
from main_server.core.stream_context import (
    StreamEmitter,
    reset_stream_emitter,
    set_stream_emitter,
)
from main_server.memory.memory_schema import ActorContext, TurnContext
from main_server.services.agent_service import agent_service
from main_server.session.session_manager import session_manager
from main_server.services.voice_services.tts_service import (
    synthesize_async,
    synthesize_sentences_async,
)


@dataclass
class ChatPipelineResult:
    text: str
    conversation_state: ConversationState
    intent: str | None = None
    tool_result: Any = None
    audio_bytes: bytes | None = None
    session_title: str | None = None
    citations: list[dict[str, Any]] | None = None


class ChatPipeline:
    """对话应用层唯一入口（Application Layer）。

    职责
    ----
    - 编排单轮对话：Agent 调用（经 agent_service）→ 可选 TTS
    - 传播运行时上下文（user_id / session_id）
    - 记录 pipeline stage（agent_invoke / tts）

    层级约定
    --------
    - **外部**（API、voice_pipeline、realtime_pipeline）只调用本类
    - **agent_service** 为内部模块，仅由本类调用，禁止外部直接
      ``agent_service.invoke()``

    语音 Pipeline 在 ASR 之后调用 ``run()`` / ``run_stream_async()``；
    文本 API 调用 ``run_async()``。
    """

    def run(
        self,
        *,
        actor: ActorContext,
        user_input: str,
    ) -> ChatPipelineResult:
        """同步执行对话（供 voice/realtime 在线程中调用，不含 TTS）。"""
        return self._invoke_agent(actor=actor, user_input=user_input)

    async def run_async(
        self,
        *,
        actor: ActorContext,
        user_input: str,
        with_audio: bool = False,
    ) -> ChatPipelineResult:
        """异步执行对话；``with_audio=True`` 时在 Pipeline 内合成 TTS。"""
        result = await asyncio.to_thread(
            self._invoke_agent,
            actor=actor,
            user_input=user_input,
        )
        if not with_audio or not result.text:
            return result

        logger.info(
            "chat.tts_start session_id=%s text_len=%s",
            actor.session_id,
            len(result.text),
        )
        try:
            async with async_pipeline_stage("tts", session_id=actor.session_id):
                audio_bytes = await synthesize_async(result.text)
        except ProviderError as exc:
            # TTS 失败（含超时 / 连接错误）不应中断整轮对话：
            # 降级为仅返回文本，由前端提示“语音合成不可用”。
            logger.warning(
                "chat.tts_skipped session_id=%s code=%s message=%s",
                actor.session_id,
                exc.code,
                exc.message,
            )
            return result
        except Exception:  # noqa: BLE001 - 兜底，避免 TTS 异常拖垮文本回复
            logger.exception(
                "chat.tts_failed session_id=%s 未预期的 TTS 异常，降级为纯文本",
                actor.session_id,
            )
            return result

        logger.info(
            "chat.tts_done session_id=%s audio_bytes=%s",
            actor.session_id,
            len(audio_bytes) if audio_bytes else 0,
        )
        return ChatPipelineResult(
            text=result.text,
            conversation_state=result.conversation_state,
            intent=result.intent,
            tool_result=result.tool_result,
            audio_bytes=audio_bytes,
            session_title=result.session_title,
            citations=result.citations,
        )

    async def run_stream_async(
        self,
        *,
        actor: ActorContext,
        user_input: str,
        emitter: StreamEmitter,
        with_tts: bool = True,
    ) -> ChatPipelineResult:
        """流式对话：Agent 文本增量推送 + 分句 TTS。"""
        result = await asyncio.to_thread(
            self._invoke_agent,
            actor=actor,
            user_input=user_input,
            emitter=emitter,
        )
        if with_tts and result.text:
            try:
                await self._stream_tts(result.text, emitter, actor.session_id)
            except ProviderError as exc:
                logger.warning(
                    "chat.stream_tts_skipped session_id=%s code=%s message=%s",
                    actor.session_id,
                    exc.code,
                    exc.message,
                )
                # TTS 失败也要通知客户端本轮结束，避免其一直等待。
                emitter.on_tts_done(0)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "chat.stream_tts_failed session_id=%s 未预期的 TTS 异常",
                    actor.session_id,
                )
                emitter.on_tts_done(0)
        return result

    def _invoke_agent(
        self,
        *,
        actor: ActorContext,
        user_input: str,
        emitter: StreamEmitter | None = None,
    ) -> ChatPipelineResult:
        user_id_var.set(actor.user_id)
        session_id_var.set(actor.session_id)

        token = None
        if emitter is not None:
            token = set_stream_emitter(emitter)

        try:
            with pipeline_stage("agent_invoke", session_id=actor.session_id):
                result = agent_service.invoke(
                    turn=TurnContext(actor=actor, user_input=user_input),
                )
        finally:
            if token is not None:
                reset_stream_emitter(token)

        intent = result.conversation_state.get("current_intent")

        title_info = session_manager.maybe_auto_title(
            actor.session_id, actor.user_id, user_input
        )

        return ChatPipelineResult(
            text=result.text,
            conversation_state=result.conversation_state,
            intent=intent,
            tool_result=result.tool_result,
            session_title=title_info.title if title_info else None,
            citations=result.citations,
        )

    async def _stream_tts(
        self,
        text: str,
        emitter: StreamEmitter,
        session_id: str,
    ) -> None:
        total = 0
        async with async_pipeline_stage("tts", session_id=session_id):
            async for index, sentence, audio_bytes in synthesize_sentences_async(
                text
            ):
                audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
                emitter.on_tts_chunk(index, sentence, audio_b64)
                total = index + 1
        emitter.on_tts_done(total)


chat_pipeline = ChatPipeline()
