"""Provider 工厂与健康检查测试。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from main_server.core.exceptions import ConfigError
from main_server.providers import bootstrap as provider_bootstrap
from main_server.providers.ASR.base import BaseASR
from main_server.providers.LLM.base import BaseLLM
from main_server.providers.registry import (
    get_asr_provider,
    get_llm_provider,
    get_tts_provider,
    list_registered_providers,
    register_asr,
    register_llm,
    register_tts,
    reset_provider_instances,
)
from main_server.providers.TTS.base import BaseTTS
from main_server.services.health_service import get_health_status


class _StubLLM(BaseLLM):
    def chat(self, messages, **kwargs):
        return "ok"

    def chat_json(self, messages, **kwargs):
        return {}

    def chat_with_tools(self, messages, tools, **kwargs):
        return {"content": "ok"}


class _StubASR(BaseASR):
    def transcribe(self, audio_path):
        return "测试"


class _StubTTS(BaseTTS):
    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        return b"audio"


@pytest.fixture(autouse=True)
def _reset_providers():
    reset_provider_instances()
    yield
    reset_provider_instances()


class TestProviderRegistry:
    def test_default_providers_registered(self) -> None:
        providers = list_registered_providers()
        assert "deepseek" in providers["llm"]
        assert "funasr" in providers["asr"]
        assert "chattts" in providers["tts"]
        assert "edge-tts" in providers["tts"]

    def test_unknown_provider_raises(self) -> None:
        with patch("main_server.providers.registry.get_settings") as mock_settings:
            mock_settings.return_value.llm.provider = "unknown-llm"
            mock_settings.return_value.models.asr.provider = "funasr"
            mock_settings.return_value.models.tts.provider = "chattts"
            with pytest.raises(ConfigError, match="LLM"):
                get_llm_provider()

    def test_runtime_switch_via_registry(self) -> None:
        register_llm("stub-llm", _StubLLM)
        register_asr("stub-asr", _StubASR)
        register_tts("stub-tts", _StubTTS)

        with patch("main_server.providers.registry.get_settings") as mock_settings:
            mock_settings.return_value.llm.provider = "stub-llm"
            mock_settings.return_value.models.asr.provider = "stub-asr"
            mock_settings.return_value.models.tts.provider = "stub-tts"

            assert isinstance(get_llm_provider(), _StubLLM)
            assert isinstance(get_asr_provider(), _StubASR)
            assert isinstance(get_tts_provider(), _StubTTS)


class TestHealthStatus:
    def test_health_reports_active_providers(self) -> None:
        provider_bootstrap.register_default_providers()
        status = get_health_status()
        assert status["active"]["llm"] == "deepseek"
        assert "components" in status
        assert status["components"]["tts"]["provider"] == "chattts"
        assert "providers" in status


class TestChatTTSProvider:
    @pytest.mark.asyncio
    async def test_synthesize_returns_wav_bytes(self) -> None:
        import numpy as np

        from main_server.providers.TTS.chattts import ChatTTSProvider

        fake_wav = np.zeros(2400, dtype=np.float32)
        with (
            patch(
                "main_server.providers.TTS.chattts.ensure_chattts_model_local",
                return_value=Path("main_server/data/models/chattts"),
            ),
            patch(
                "main_server.providers.TTS.chattts._get_chat_model",
            ) as mock_get_chat,
            patch(
                "main_server.providers.TTS.chattts._resolve_speaker",
                return_value="speaker",
            ),
            patch(
                "main_server.providers.TTS.chattts._wav_to_bytes",
                return_value=b"wav-bytes",
            ),
            patch(
                "main_server.providers.TTS.chattts.call_with_retry",
                side_effect=lambda fn, **_kwargs: fn(),
            ),
        ):
            mock_chat = mock_get_chat.return_value
            mock_chat.infer.return_value = [fake_wav]
            provider = ChatTTSProvider()
            result = await provider.synthesize("你好")
        assert result == b"wav-bytes"
        mock_chat.infer.assert_called_once()


class TestEdgeTTSProvider:
    @pytest.mark.asyncio
    async def test_synthesize_resolves_settings(self) -> None:
        from main_server.providers.TTS.edge_tts import EdgeTTSProvider

        with patch(
            "main_server.core.provider_retry.async_call_with_retry",
            new_callable=AsyncMock,
        ) as mock_retry:
            mock_retry.return_value = b"audio-bytes"
            provider = EdgeTTSProvider()
            result = await provider.synthesize("你好", "zh-CN-XiaoxiaoNeural")
        assert result == b"audio-bytes"
        mock_retry.assert_awaited_once()
