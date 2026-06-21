from __future__ import annotations

import base64

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from main_server.api.deps.auth_dep import CurrentUser, require_business_user
from main_server.core.context import session_id_var, user_id_var
from main_server.core.logger import logger
from main_server.memory.memory_schema import ActorContext
from main_server.services.pipeline.chat_pipeline import chat_pipeline
from main_server.session.session_manager import session_manager

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    with_audio: bool = False


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    audio_base64: str | None = None
    intent: str | None = None
    session_title: str | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    current_user: CurrentUser = Depends(require_business_user),
):
    user_id_var.set(current_user.user_id)
    session_id = session_manager.ensure_session(
        body.session_id, current_user.user_id
    )
    session_id_var.set(session_id)
    session_manager.touch(session_id, current_user.user_id)
    logger.info(
        "api.chat session_id=%s channel=text with_audio=%s message_len=%s",
        session_id,
        body.with_audio,
        len(body.message),
    )

    actor = ActorContext.from_current_user(
        current_user, session_id=session_id, channel="text"
    )

    result = await chat_pipeline.run_async(
        actor=actor,
        user_input=body.message,
        with_audio=body.with_audio,
    )

    audio_base64 = None
    if result.audio_bytes:
        audio_base64 = base64.b64encode(result.audio_bytes).decode("ascii")

    logger.info(
        "api.chat.response session_id=%s reply_len=%s with_audio=%s has_audio=%s audio_bytes=%s",
        session_id,
        len(result.text or ""),
        body.with_audio,
        audio_base64 is not None,
        len(result.audio_bytes) if result.audio_bytes else 0,
    )

    return ChatResponse(
        session_id=session_id,
        reply=result.text,
        audio_base64=audio_base64,
        intent=result.intent,
        session_title=result.session_title,
    )
