"""Audio API 测试（mock ASR/Agent/TTS）。"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from main_server.api.audio import router as audio_router
from main_server.core.auth.permission import Role
from tests.conftest import auth_headers, make_test_app, token_for_user


@pytest.fixture
def audio_client(
    memory_db, mock_agent_invoke, mock_asr, mock_tts, tmp_path, monkeypatch
) -> TestClient:
    mock_agent_invoke("语音回复内容")
    monkeypatch.setattr(
        "main_server.utils.audio_utils.TEMP_AUDIO_DIR", tmp_path
    )
    return TestClient(make_test_app(audio_router))


@pytest.fixture
def sales_token(memory_db) -> str:
    from main_server.core.auth.user_service import create_user
    from main_server.DB import db_session

    with db_session() as session:
        user = create_user(
            session,
            username="audio_sales",
            password="audio1234",
            roles=[Role.SALES],
        )
        return token_for_user(user.id, "audio_sales", [Role.SALES])


class TestAudioAPI:
    def test_upload_wav_success(
        self, audio_client: TestClient, sales_token: str
    ) -> None:
        # 场景：上传 wav；输入：假 wav 文件；预期：transcript + reply + audio
        resp = audio_client.post(
            "/api/audio",
            headers=auth_headers(sales_token),
            data={"with_audio": "true"},
            files={"file": ("test.wav", io.BytesIO(b"fake-wav"), "audio/wav")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["transcript"] == "你好，这是测试语音"
        assert data["reply"] == "语音回复内容"
        assert data["audio_base64"]
        assert data["session_id"]

    def test_upload_without_audio_skips_tts(
        self, audio_client: TestClient, sales_token: str, monkeypatch
    ) -> None:
        called = {"tts": False}

        async def _synthesize(text: str) -> bytes:
            called["tts"] = True
            return b"fake-audio-bytes"

        monkeypatch.setattr(
            "main_server.services.pipeline.chat_pipeline.synthesize_async",
            _synthesize,
        )
        resp = audio_client.post(
            "/api/audio",
            headers=auth_headers(sales_token),
            data={"with_audio": "false"},
            files={"file": ("test.wav", io.BytesIO(b"fake-wav"), "audio/wav")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["transcript"] == "你好，这是测试语音"
        assert data["reply"] == "语音回复内容"
        assert data["audio_base64"] is None
        assert called["tts"] is False

    def test_no_file(self, audio_client: TestClient, sales_token: str) -> None:
        # 场景：缺少文件；输入：无 file；预期：422
        resp = audio_client.post(
            "/api/audio",
            headers=auth_headers(sales_token),
        )
        assert resp.status_code == 422

    def test_no_auth(self, audio_client: TestClient) -> None:
        # 场景：未鉴权；输入：无 token；预期：401
        resp = audio_client.post(
            "/api/audio",
            files={"file": ("t.wav", io.BytesIO(b"x"), "audio/wav")},
        )
        assert resp.status_code == 401

    def test_with_session_id(
        self, audio_client: TestClient, sales_token: str
    ) -> None:
        # 场景：携带 session_id；输入：form session_id；预期：复用会话
        r1 = audio_client.post(
            "/api/audio",
            headers=auth_headers(sales_token),
            files={"file": ("t.wav", io.BytesIO(b"x"), "audio/wav")},
        )
        sid = r1.json()["session_id"]
        r2 = audio_client.post(
            "/api/audio",
            headers=auth_headers(sales_token),
            data={"session_id": sid},
            files={"file": ("t2.wav", io.BytesIO(b"y"), "audio/wav")},
        )
        assert r2.json()["session_id"] == sid
