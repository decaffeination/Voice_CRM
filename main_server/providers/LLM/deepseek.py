from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any, Iterator

import httpx

from main_server.config.settings import get_settings
from main_server.core.exceptions import ConfigError, LLMError
from main_server.core.logger import logger
from main_server.core.provider_errors import raise_llm_error
from main_server.core.provider_retry import call_with_retry
from main_server.core.provider_timeouts import resolve_provider_timeout
from main_server.providers.LLM.base import BaseLLM

_RETRYABLE = (httpx.HTTPError, httpx.TimeoutException)
_PROVIDER = "deepseek"


class DeepSeekLLM(BaseLLM):
    def __init__(self) -> None:
        settings = get_settings().llm
        self._api_key = settings.api_key
        self._base_url = settings.base_url.rstrip("/")
        self._model = settings.model

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ConfigError(
                "未配置 LLM API Key，请设置环境变量 LLM_API_KEY（见 .env.example）"
            )
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/v1/chat/completions"
        timeout = resolve_provider_timeout("llm")

        def do_post() -> dict[str, Any]:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, headers=self._headers(), json=payload)
                response.raise_for_status()
                return response.json()

        start = time.perf_counter()
        try:
            data = call_with_retry(
                do_post,
                provider=_PROVIDER,
                retryable=_RETRYABLE,
                thread_timeout=False,
            )
        except _RETRYABLE as exc:
            logger.exception("llm.call_failed provider=%s model=%s", _PROVIDER, self._model)
            raise_llm_error(exc, provider=_PROVIDER)

        duration_ms = (time.perf_counter() - start) * 1000
        usage = data.get("usage") or {}
        logger.info(
            "llm.call provider=%s model=%s duration_ms=%.1f "
            "prompt_tokens=%s completion_tokens=%s total_tokens=%s",
            _PROVIDER,
            self._model,
            duration_ms,
            usage.get("prompt_tokens", "-"),
            usage.get("completion_tokens", "-"),
            usage.get("total_tokens", "-"),
        )
        return data

    def _extract_content(self, data: dict[str, Any]) -> str:
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM 响应格式异常", provider=_PROVIDER) from exc

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.3),
        }
        data = self._post(payload)
        return self._extract_content(data)

    def chat_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "response_format": {"type": "json_object"},
        }
        data = self._post(payload)
        content = self._extract_content(data)
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(
                f"LLM 返回非 JSON: {content[:200]}",
                provider=_PROVIDER,
            ) from exc

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
            "tools": tools,
            "tool_choice": kwargs.get("tool_choice", "auto"),
        }
        data = self._post(payload)
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM 响应格式异常", provider=_PROVIDER) from exc
        return dict(message)

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Iterator[str]:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.3),
            "stream": True,
        }
        url = f"{self._base_url}/v1/chat/completions"
        timeout = resolve_provider_timeout("llm")
        max_retries, retry_delay = get_settings().providers.max_retries, get_settings().providers.retry_delay_seconds

        start = time.perf_counter()
        total_chars = 0
        last_exc: BaseException | None = None

        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=timeout) as client:
                    with client.stream(
                        "POST",
                        url,
                        headers=self._headers(),
                        json=payload,
                    ) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if not line or not line.startswith("data: "):
                                continue
                            data_text = line[6:].strip()
                            if data_text == "[DONE]":
                                break
                            try:
                                data = json.loads(data_text)
                            except json.JSONDecodeError:
                                continue
                            try:
                                delta = data["choices"][0]["delta"].get("content") or ""
                            except (KeyError, IndexError, TypeError):
                                delta = ""
                            if delta:
                                total_chars += len(delta)
                                yield delta
                duration_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "llm.stream provider=%s model=%s duration_ms=%.1f chars=%s",
                    _PROVIDER,
                    self._model,
                    duration_ms,
                    total_chars,
                )
                return
            except _RETRYABLE as exc:
                last_exc = exc
                if attempt >= max_retries:
                    break
                logger.warning(
                    "llm.stream_retry provider=%s attempt=%s/%s",
                    _PROVIDER,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(retry_delay)

        logger.exception(
            "llm.stream_failed provider=%s model=%s", _PROVIDER, self._model
        )
        assert last_exc is not None
        raise_llm_error(last_exc, provider=_PROVIDER)


@lru_cache
def get_llm() -> BaseLLM:
    """兼容别名；请优先使用 ``main_server.providers.registry.get_llm_provider``。"""
    from main_server.providers.registry import get_llm_provider

    return get_llm_provider()
