"""上传音频 HTTP 验收（需 llm.api_key；ASR/TTS 模型首次可自动下载）。

测试音频默认使用 tests/fixtures/recording.wav（需自行放置清晰人声录音）。

pytest 等价: api/test_audio_api.py、integration/test_voice_pipeline.py

用法:
  # 先将录音放到 tests/fixtures/recording.wav
  python tests/live/scripts/http_audio_upload.py
  python tests/live/scripts/http_audio_upload.py --switch
  python tests/live/scripts/http_audio_upload.py --audio path/to/your.wav
  python -m main_server.utils.download_asr_model   # 可选：预下载 ASR
"""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _audio_fixture import FIXTURE_SAMPLE, ensure_audio
from _http_common import BASE_URL, json_request, login

DEFAULT_AUDIO = FIXTURE_SAMPLE


def upload(token: str, audio: Path, session_id: str | None = None) -> dict:
    import httpx

    headers = {"Authorization": f"Bearer {token}"}
    data = {"session_id": session_id} if session_id else None
    with audio.open("rb") as handle:
        files = {"file": (audio.name, handle, "audio/wav")}
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(
                f"{BASE_URL}/api/audio",
                headers=headers,
                files=files,
                data=data,
            )
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
    return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="音频上传 HTTP 验收")
    parser.add_argument("--audio", type=Path, default=DEFAULT_AUDIO)
    parser.add_argument("--session-id")
    parser.add_argument("--switch", action="store_true")
    args = parser.parse_args()

    audio_path = ensure_audio(args.audio)
    token = login()
    result = upload(token, audio_path, args.session_id)
    print("transcript:", result.get("transcript"))
    print("reply:", result.get("reply"))
    sid = result.get("session_id")
    if args.switch and sid:
        r = json_request(
            "POST",
            "/api/chat",
            token=token,
            body={
                "message": "还有请假流程吗",
                "session_id": sid,
                "with_audio": False,
            },
        )
        print("文字跟进:", r.get("reply"))
    out = PROJECT_ROOT / "tests" / "live_audio_reply.mp3"
    b64 = result.get("audio_base64")
    if b64:
        out.write_bytes(base64.b64decode(b64))
        print("TTS 已保存:", out)


if __name__ == "__main__":
    main()
