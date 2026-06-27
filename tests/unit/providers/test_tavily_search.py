"""Tavily 搜索 Provider 单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from main_server.providers.Tools.tavily_search import TavilySearchProvider


class TestTavilySearchProvider:
    @patch("main_server.providers.Tools.tavily_search.get_settings")
    @patch("main_server.providers.Tools.tavily_search.call_with_retry")
    def test_search_returns_results(
        self, mock_retry: MagicMock, mock_settings: MagicMock
    ) -> None:
        settings = MagicMock()
        settings.tools.web_search.enabled = True
        settings.tools.web_search.tavily_api_key = "test-key"
        settings.tools.web_search.max_results = 3
        settings.tools.web_search.timeout_seconds = 10.0
        mock_settings.return_value = settings
        mock_retry.return_value = [
            {"title": "A", "url": "https://a.com", "snippet": "hello"}
        ]

        provider = TavilySearchProvider()
        result = provider.search("测试")
        assert result["provider"] == "tavily"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "A"

    @patch("main_server.providers.Tools.tavily_search.get_settings")
    def test_search_missing_api_key(self, mock_settings: MagicMock) -> None:
        settings = MagicMock()
        settings.tools.web_search.enabled = True
        settings.tools.web_search.tavily_api_key = ""
        mock_settings.return_value = settings

        provider = TavilySearchProvider()
        result = provider.search("测试")
        assert result["error"] == "tavily_api_key_missing"
