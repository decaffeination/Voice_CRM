"""LLM 业务封装层：统一 chat / chat_json / chat_with_tools 入口。"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from main_server.providers.LLM.base import BaseLLM
from main_server.providers import bootstrap as _providers_bootstrap  # noqa: F401
from main_server.providers.registry import get_llm_provider


class LLMService:
    """对外提供 LLM 能力；内部委托 Provider（DeepSeek）。"""

    def _provider(self) -> BaseLLM:
        return get_llm_provider()

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return self._provider().chat(messages, **kwargs)

    def chat_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        return self._provider().chat_json(messages, **kwargs)

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self._provider().chat_with_tools(messages, tools, **kwargs)

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Iterator[str]:
        return self._provider().chat_stream(messages, **kwargs)

    def summarize_dialog(self, prompt: str) -> str:
        """Memory 摘要等场景。"""
        return self.chat(
            [
                {"role": "system", "content": "你是对话摘要助手。"},
                {"role": "user", "content": prompt},
            ]
        )


llm_service = LLMService()
