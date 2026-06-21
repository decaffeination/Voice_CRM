"""WebSocket 实时语音验收（需 ASR + VAD + llm.api_key）。

pytest 等价: unit/core/test_ws_errors.py（协议层）；全链路仅 live

用法:
  # 先将录音放到 tests/fixtures/recording.wav
  python -m main_server.utils.download_vad_model   # 首次
  python tests/live/scripts/websocket_realtime_voice.py
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _audio_fixture import FIXTURE_SAMPLE, ensure_audio
from _http_common import chat, create_session, login

WS_BASE = "ws://127.0.0.1:8000"
DEFAULT_AUDIO = FIXTURE_SAMPLE
ASR_MODEL = (
    PROJECT_ROOT / "main_server" / "data" / "models" / "SenseVoiceSmall" / "model.pt"
)
VAD_MODEL = (
    PROJECT_ROOT
    / "main_server"
    / "data"
    / "models"
    / "silero_vad"
    / "silero_vad_op18_ifless.onnx"
)
CHUNK_BYTES = 3200


def wav_to_pcm(path: Path) -> bytes:
    import numpy as np
    import librosa

    samples, _ = librosa.load(str(path), sr=16000, mono=True)
    return (np.clip(samples, -1.0, 1.0) * 32767.0).astype("int16").tobytes()


async def run_ws(token: str, session_id: str, audio: Path, fast: bool) -> dict:
    import websockets

    uri = f"{WS_BASE}/ws/audio/{session_id}?token={token}"
    pcm = wav_to_pcm(audio)
    collected: dict = {}

    async with websockets.connect(
        uri,
        open_timeout=30,
        ping_interval=30,
        ping_timeout=120,
        close_timeout=10,
    ) as ws:
        ready = json.loads(await ws.recv())
        if ready.get("type") != "ready":
            raise RuntimeError(ready)

        for offset in range(0, len(pcm), CHUNK_BYTES):
            chunk = pcm[offset : offset + CHUNK_BYTES]
            await ws.send(
                json.dumps(
                    {
                        "type": "audio",
                        "data": base64.b64encode(chunk).decode("ascii"),
                    }
                )
            )
            if not fast:
                await asyncio.sleep(CHUNK_BYTES / 32000)

        await ws.send(json.dumps({"type": "end"}))

        audio_chunks: list[str] = []
        done_rounds = 0
        while True:
            # 首轮等待较久（ChatTTS CPU 合成可能数十秒）；收到一轮 tts_done
            # 后只再等一小段时间，处理 VAD 可能切出的额外语音段。
            recv_timeout = 15 if done_rounds > 0 else 300
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=recv_timeout)
            except TimeoutError:
                if done_rounds > 0:
                    break
                raise TimeoutError(
                    "等待服务端响应超时；ChatTTS(CPU) 较慢可改用 edge-tts 或加大超时"
                ) from None
            msg = json.loads(raw)
            t = msg.get("type")
            if t == "asr_final":
                collected["transcript"] = msg.get("text")
            elif t == "agent_text":
                collected["reply"] = msg.get("text")
            elif t == "agent_text_delta":
                collected["reply"] = (collected.get("reply") or "") + msg.get(
                    "delta", ""
                )
            elif t == "tts_audio_chunk":
                data = msg.get("data")
                if data:
                    audio_chunks.append(data)
            elif t == "tts_audio":
                # 兼容旧协议（若服务端仍发送整段音频）
                data = msg.get("data")
                if data:
                    audio_chunks.append(data)
                done_rounds += 1
            elif t == "tts_done":
                done_rounds += 1
                collected["tts_chunk_count"] = msg.get(
                    "total_chunks", len(audio_chunks)
                )
            elif t == "error":
                raise RuntimeError(msg.get("message"))

        if audio_chunks:
            collected["audio_chunks"] = audio_chunks

    return collected


def main() -> None:
    parser = argparse.ArgumentParser(description="WebSocket 实时语音验收")
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--session-id")
    parser.add_argument("--switch", action="store_true")
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()

    if not ASR_MODEL.exists() or not VAD_MODEL.exists():
        raise SystemExit("缺少 ASR 或 VAD 模型，见 tests/live/README.md")

    audio_path = ensure_audio(args.audio)
    token = login()
    sid = args.session_id or create_session(token, "WS语音验收")
    print(f"使用音频: {audio_path}")
    result = asyncio.run(run_ws(token, sid, audio_path, args.fast))
    print("transcript:", result.get("transcript"))
    reply = result.get("reply")
    if reply:
        preview = reply if len(reply) <= 200 else reply[:200] + "..."
        print("reply:", preview)
    chunks = result.get("audio_chunks") or []
    tts_count = result.get("tts_chunk_count", len(chunks))
    if chunks:
        out = PROJECT_ROOT / "tests" / "live_ws_reply.mp3"
        out.write_bytes(b"".join(base64.b64decode(c) for c in chunks))
        print("TTS 已保存:", out, f"({len(chunks)} 段)")
    elif tts_count == 0:
        print("TTS 已跳过（连接失败或未合成），文字链路正常")
    if args.switch:
        r = chat(token, sid, "还有请假流程吗")
        print("文字跟进:", r.get("reply"))


if __name__ == "__main__":
    main()
