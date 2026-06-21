from __future__ import annotations

import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from main_server.api.websocket.connection_manager import connection_manager
from main_server.core.auth.jwt_auth import get_current_user_from_token
from main_server.core.auth.permission import user_has_business_role
from main_server.core.provider_timeouts import resolve_provider_timeout
from main_server.core.context import (
    new_request_id,
    request_id_var,
    session_id_var,
    user_id_var,
)
from main_server.core.exceptions import AppError, AuthError, PermissionDeniedError
from main_server.core.logger import logger
from main_server.core.ws_errors import send_ws_error
from main_server.memory.memory_schema import ActorContext
from main_server.services.pipeline.realtime_pipeline import RealtimePipeline
from main_server.session.session_manager import session_manager


class WSService:
    async def handle_audio_connection(
        self,
        websocket: WebSocket,
        session_id: str,
        token: str,
    ) -> None:
        request_id = new_request_id()
        request_id_var.set(request_id)
        session_id_var.set(session_id)

        await websocket.accept()

        try:
            user = get_current_user_from_token(token)
        except AuthError as exc:
            logger.warning("ws.auth_failed session_id=%s code=%s", session_id, exc.code)
            await send_ws_error(websocket, exc, stage="auth")
            await websocket.close(code=1008, reason="认证失败")
            return

        user_id_var.set(user.user_id)

        if not user_has_business_role(user):
            logger.warning(
                "ws.role_denied session_id=%s user_id=%s roles=%s",
                session_id,
                user.user_id,
                user.roles,
            )
            await send_ws_error(
                websocket,
                PermissionDeniedError("无权使用语音对话功能"),
                stage="auth",
            )
            await websocket.close(code=1008, reason="无权访问")
            return

        try:
            session_manager.get(session_id, user.user_id)
        except AppError as exc:
            logger.warning(
                "ws.session_invalid session_id=%s code=%s",
                session_id,
                exc.code,
            )
            await send_ws_error(websocket, exc, stage="session")
            await websocket.close(code=1008, reason="会话无效")
            return

        await connection_manager.connect(session_id, websocket, accept=False)
        actor = ActorContext.from_current_user(
            user, session_id=session_id, channel="ws"
        )
        pipeline = RealtimePipeline(actor)
        logger.info(
            "ws.connected session_id=%s user_id=%s",
            session_id,
            user.user_id,
        )

        idle_timeout = resolve_provider_timeout("ws")
        try:
            await pipeline.send(
                websocket,
                "ready",
                session_id=session_id,
                request_id=request_id,
            )
            while True:
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=idle_timeout,
                    )
                except TimeoutError:
                    logger.info(
                        "ws.idle_timeout session_id=%s timeout_s=%s",
                        session_id,
                        idle_timeout,
                    )
                    await websocket.close(code=1000, reason="空闲超时")
                    break
                msg_type = message.get("type", "")
                if msg_type not in ("audio", "ping"):
                    logger.info("ws.message type=%s", msg_type)
                await pipeline.handle(message, websocket)
        except WebSocketDisconnect:
            logger.info("ws.disconnected session_id=%s", session_id)
        finally:
            connection_manager.disconnect(session_id)
            pipeline.reset_state()


ws_service = WSService()
