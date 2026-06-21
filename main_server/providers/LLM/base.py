from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any


class BaseLLM(ABC):
    @abstractmethod
    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """返回 assistant 文本内容。"""

    @abstractmethod
    def chat_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        """返回 JSON 对象。"""

    @abstractmethod
    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Function Calling：返回 assistant message 字典（含 content / tool_calls）。"""

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Iterator[str]:
        """流式返回 assistant 文本增量；默认退化为一次性输出。"""
        yield self.chat(messages, **kwargs)
