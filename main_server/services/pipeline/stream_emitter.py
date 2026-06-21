"""WebSocket 流式消息发送器。"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine


class AsyncWsStreamEmitter:
    """将 StreamEmitter 回调调度到 asyncio event loop。"""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        send_fn: Callable[..., Coroutine[Any, Any, None]],
        websocket: Any,
    ) -> None:
        self._loop = loop
        self._send = send_fn
        self._ws = websocket

    def _schedule(self, coro: Coroutine[Any, Any, None]) -> None:
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    def on_text_delta(self, delta: str) -> None:
        if not delta:
            return
        self._schedule(self._send(self._ws, "agent_text_delta", delta=delta))

    def on_text_final(self, text: str, *, intent: str | None = None) -> None:
        payload: dict[str, Any] = {"text": text}
        if intent is not None:
            payload["intent"] = intent
        self._schedule(self._send(self._ws, "agent_text", **payload))

    def on_tts_chunk(
        self, index: int, sentence: str, audio_base64: str
    ) -> None:
        self._schedule(
            self._send(
                self._ws,
                "tts_audio_chunk",
                index=index,
                sentence=sentence,
                data=audio_base64,
            )
        )

    def on_tts_done(self, total_chunks: int) -> None:
        self._schedule(
            self._send(self._ws, "tts_done", total_chunks=total_chunks)
        )
