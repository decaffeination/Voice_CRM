"""流式输出上下文（contextvars），供 Agent response_node 回调 Pipeline。"""

from __future__ import annotations

import contextvars
from typing import Any, Protocol


class StreamEmitter(Protocol):
    """同步回调接口；异步 Pipeline 实现时内部 schedule 到 event loop。"""

    def on_text_delta(self, delta: str) -> None: ...

    def on_text_final(
        self,
        text: str,
        *,
        intent: str | None = None,
        citations: list[dict[str, Any]] | None = None,
    ) -> None: ...

    def on_tts_chunk(
        self, index: int, sentence: str, audio_base64: str
    ) -> None: ...

    def on_tts_done(self, total_chunks: int) -> None: ...


stream_emitter_var: contextvars.ContextVar[StreamEmitter | None] = (
    contextvars.ContextVar("stream_emitter", default=None)
)


def get_stream_emitter() -> StreamEmitter | None:
    return stream_emitter_var.get()


def set_stream_emitter(emitter: StreamEmitter | None) -> contextvars.Token:
    return stream_emitter_var.set(emitter)


def reset_stream_emitter(token: contextvars.Token) -> None:
    stream_emitter_var.reset(token)
