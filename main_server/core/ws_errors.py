"""WebSocket 统一错误协议。"""

from __future__ import annotations

from typing import Any, Protocol

from main_server.core.context import get_request_id
from main_server.core.exceptions import (
    AppError,
    InternalServerError,
    PipelineError,
    ProviderError,
)
from main_server.core.logger import logger


class WebSocketSender(Protocol):
    async def send_json(self, data: dict[str, Any]) -> None: ...


def build_ws_error_payload(
    exc: BaseException,
    *,
    stage: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "error",
        "request_id": get_request_id(),
    }

    if isinstance(exc, AppError):
        payload["code"] = exc.code
        payload["message"] = exc.message
        if isinstance(exc, PipelineError) and exc.stage:
            payload["stage"] = exc.stage
        elif isinstance(exc, ProviderError) and exc.provider:
            payload["provider"] = exc.provider
        elif stage:
            payload["stage"] = stage
        return payload

    logger.exception("ws.unhandled_error stage=%s", stage or "-")
    internal = InternalServerError()
    payload["code"] = internal.code
    payload["message"] = internal.message
    if stage:
        payload["stage"] = stage
    return payload


async def send_ws_error(
    websocket: WebSocketSender,
    exc: BaseException,
    *,
    stage: str | None = None,
) -> None:
    await websocket.send_json(build_ws_error_payload(exc, stage=stage))
