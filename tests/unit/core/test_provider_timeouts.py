"""Provider 分项超时配置测试。"""

from __future__ import annotations

from types import SimpleNamespace

from main_server.config.settings import KnowledgeSettings, ProviderSettings
from main_server.core.provider_timeouts import resolve_provider_timeout


class TestResolveProviderTimeout:
    def test_llm_alias(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "main_server.core.provider_timeouts.get_settings",
            lambda: _mock_settings(
                ProviderSettings(
                    llm_timeout_seconds=55,
                    asr_timeout_seconds=90,
                    tts_timeout_seconds=45,
                )
            ),
        )
        assert resolve_provider_timeout("deepseek") == 55.0
        assert resolve_provider_timeout("llm") == 55.0

    def test_asr_and_tts(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "main_server.core.provider_timeouts.get_settings",
            lambda: _mock_settings(
                ProviderSettings(
                    asr_timeout_seconds=120,
                    tts_timeout_seconds=30,
                )
            ),
        )
        assert resolve_provider_timeout("funasr") == 120.0
        assert resolve_provider_timeout("chattts") == 30.0
        assert resolve_provider_timeout("edge-tts") == 30.0

    def test_pipeline_ws_and_knowledge(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "main_server.core.provider_timeouts.get_settings",
            lambda: _mock_settings(
                ProviderSettings(
                    pipeline_timeout_seconds=200,
                    ws_idle_timeout_seconds=400,
                ),
                knowledge=KnowledgeSettings(timeout_seconds=25),
            ),
        )
        assert resolve_provider_timeout("pipeline") == 200.0
        assert resolve_provider_timeout("ws") == 400.0
        assert resolve_provider_timeout("knowledge") == 25.0

    def test_unknown_provider_fallback(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "main_server.core.provider_timeouts.get_settings",
            lambda: _mock_settings(ProviderSettings(timeout_seconds=77)),
        )
        assert resolve_provider_timeout("unknown-provider") == 77.0


def _mock_settings(
    providers: ProviderSettings,
    knowledge: KnowledgeSettings | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        providers=providers,
        knowledge=knowledge or KnowledgeSettings(),
    )
