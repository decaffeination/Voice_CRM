"""Provider 调用超时与重试。"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from main_server.config.settings import get_settings
from main_server.core.logger import logger
from main_server.core.provider_timeouts import resolve_provider_timeout

T = TypeVar("T")


def _retry_settings() -> tuple[int, float]:
    cfg = get_settings().providers
    return cfg.max_retries, cfg.retry_delay_seconds


def _deadline(provider: str, timeout: float | None) -> float:
    return timeout if timeout is not None else resolve_provider_timeout(provider)


def _run_with_thread_timeout(fn: Callable[[], T], timeout: float) -> T:
    """在线程中执行同步调用，超时则抛出 TimeoutError。"""
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="provider") as pool:
        future = pool.submit(fn)
        return future.result(timeout=timeout)


def call_with_retry(
    fn: Callable[[], T],
    *,
    provider: str,
    retryable: tuple[type[BaseException], ...] = (Exception,),
    timeout: float | None = None,
    thread_timeout: bool = True,
) -> T:
    max_retries, retry_delay = _retry_settings()
    deadline = _deadline(provider, timeout)
    last_exc: BaseException | None = None

    for attempt in range(max_retries + 1):
        try:
            if thread_timeout:
                return _run_with_thread_timeout(fn, deadline)
            return fn()
        except TimeoutError:
            logger.warning(
                "provider.timeout provider=%s timeout_s=%s",
                provider,
                deadline,
            )
            raise
        except retryable as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            logger.warning(
                "provider.retry provider=%s attempt=%s/%s",
                provider,
                attempt + 1,
                max_retries,
            )
            time.sleep(retry_delay)

    assert last_exc is not None
    raise last_exc


async def async_call_with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    provider: str,
    retryable: tuple[type[BaseException], ...] = (Exception,),
    timeout: float | None = None,
) -> T:
    max_retries, retry_delay = _retry_settings()
    deadline = _deadline(provider, timeout)
    last_exc: BaseException | None = None

    for attempt in range(max_retries + 1):
        try:
            return await asyncio.wait_for(fn(), timeout=deadline)
        except TimeoutError:
            logger.warning(
                "provider.timeout provider=%s timeout_s=%s",
                provider,
                deadline,
            )
            raise
        except retryable as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            logger.warning(
                "provider.retry provider=%s attempt=%s/%s",
                provider,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(retry_delay)

    assert last_exc is not None
    raise last_exc
