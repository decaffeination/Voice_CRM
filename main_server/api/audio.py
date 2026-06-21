from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel

from main_server.api.deps.auth_dep import CurrentUser, require_business_user
from main_server.core.context import session_id_var, user_id_var
from main_server.core.logger import logger
from main_server.memory.memory_schema import ActorContext
from main_server.services.pipeline.voice_pipeline import voice_pipeline
from main_server.session.session_manager import session_manager
from main_server.utils.audio_utils import cleanup_file, save_upload_bytes

router = APIRouter(prefix="/api", tags=["audio"])


class AudioChatResponse(BaseModel):
    session_id: str
    transcript: str
    reply: str
    audio_base64: str | None = None
    intent: str | None = None
    session_title: str | None = None


@router.post("/audio", response_model=AudioChatResponse)
async def audio_chat(
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
    with_audio: bool = Form(default=False),
    current_user: CurrentUser = Depends(require_business_user),
):
    user_id_var.set(current_user.user_id)
    temp_path = None
    try:
        session_id = session_manager.ensure_session(
            session_id, current_user.user_id
        )
        session_id_var.set(session_id)
        session_manager.touch(session_id, current_user.user_id)

        suffix = ""
        if file.filename and "." in file.filename:
            suffix = "." + file.filename.rsplit(".", 1)[-1]
        content = await file.read()
        temp_path = save_upload_bytes(content, suffix or ".wav")
        logger.info(
            "api.audio session_id=%s channel=voice with_audio=%s file_bytes=%s suffix=%s",
            session_id,
            with_audio,
            len(content),
            suffix or ".wav",
        )

        actor = ActorContext.from_current_user(
            current_user, session_id=session_id, channel="voice"
        )

        result = await voice_pipeline.run_from_file(
            temp_path,
            actor=actor,
            with_audio=with_audio,
        )

        audio_base64 = None
        if result.audio_bytes:
            audio_base64 = base64.b64encode(result.audio_bytes).decode("ascii")

        return AudioChatResponse(
            session_id=session_id,
            transcript=result.transcript,
            reply=result.text,
            audio_base64=audio_base64,
            intent=result.intent,
            session_title=result.session_title,
        )
    finally:
        if temp_path is not None:
            cleanup_file(temp_path)
