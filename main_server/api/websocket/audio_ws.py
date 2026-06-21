from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket

from main_server.services.voice_services.ws_service import ws_service

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/audio/{session_id}")
async def audio_websocket(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(..., description="JWT access_token"),
):
    """
    实时语音 WebSocket。

    客户端 → 服务端:
      {"type": "ping"}
      {"type": "audio", "data": "<base64 pcm 16kHz mono int16>"}
      {"type": "end", "with_tts": true}   # 结束当前语音段，触发 VAD flush
      {"type": "reset"}                   # 重置 VAD 状态

    服务端 → 客户端:
      {"type": "ready", "session_id": "...", "request_id": "..."}
      {"type": "pong"}
      {"type": "asr_final", "text": "..."}
      {"type": "agent_text_delta", "delta": "..."}
      {"type": "agent_text", "text": "...", "intent": "..."}
      {"type": "tts_audio_chunk", "index": 0, "sentence": "...", "data": "<base64>"}
      {"type": "tts_done", "total_chunks": N}      # 本轮 TTS 结束（失败时 N=0）
      {"type": "error", "code": "...", "message": "...", "request_id": "...", "stage": "..."}
    """
    await ws_service.handle_audio_connection(websocket, session_id, token)
