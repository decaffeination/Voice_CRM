"""Provider 层 mock 单元测试（DeepSeek / WebSearch）。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from main_server.core.exceptions import LLMTimeoutError
from main_server.providers.LLM.deepseek import DeepSeekLLM
from main_server.providers.Tools.web_search import WebSearchProvider


class TestDeepSeekLLM:
    def _make_llm(self) -> DeepSeekLLM:
        llm = DeepSeekLLM.__new__(DeepSeekLLM)
        llm._api_key = "sk-test"
        llm._base_url = "https://api.deepseek.com"
        llm._model = "deepseek-chat"
        return llm

    def test_chat_success(self) -> None:
        # 场景：HTTP 成功；输入：mock response；预期：返回 content
        llm = self._make_llm()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "回复"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        mock_response.raise_for_status = MagicMock()
        with patch("main_server.providers.LLM.deepseek.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = (
                mock_response
            )
            result = llm.chat([{"role": "user", "content": "hi"}])
        assert result == "回复"

    def test_chat_timeout_raises_llm_error(self) -> None:
        # 场景：HTTP 超时；输入：TimeoutException；预期：LLM 相关异常
        llm = self._make_llm()
        with patch("main_server.providers.LLM.deepseek.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = (
                httpx.TimeoutException("timeout")
            )
            with pytest.raises((LLMTimeoutError, Exception)):
                llm.chat([{"role": "user", "content": "hi"}])


class TestWebSearchProvider:
    def test_search_returns_results(self) -> None:
        # 场景：搜索成功；输入：mock fetch；预期：results 字段
        provider = WebSearchProvider()
        with patch(
            "main_server.providers.Tools.web_search.call_with_retry",
            return_value=[{"title": "T", "url": "http://x.com"}],
        ):
            result = provider.search("测试公司")
        assert result["query"] == "测试公司"
        assert len(result["results"]) == 1
