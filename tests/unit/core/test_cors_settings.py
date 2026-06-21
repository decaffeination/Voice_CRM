"""CORS 配置单元测试。"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from main_server.config.cors import CORSSettings
from main_server.config.settings import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestCORSSettings:
    def test_default_wildcard(self) -> None:
        cors = CORSSettings()
        assert cors.resolved_origins == ["*"]
        assert cors.uses_wildcard is True

    def test_env_override_comma_separated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
        with patch(
            "main_server.config.settings._load_yaml_config",
            return_value={"jwt": {"secret_key": "test-secret-key-at-least-32-chars"}},
        ):
            settings = get_settings()
        assert settings.cors.resolved_origins == [
            "http://a.test",
            "http://b.test",
        ]
        assert settings.cors.uses_wildcard is False

    def test_yaml_config(self) -> None:
        cors = CORSSettings(
            allow_origins=["https://app.example.com"],
            allow_credentials=True,
        )
        assert cors.resolved_origins == ["https://app.example.com"]
