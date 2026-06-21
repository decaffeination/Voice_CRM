"""知识库存储层异常守卫。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from main_server.core.exceptions import AppError, KnowledgeError, KnowledgeTimeoutError
from main_server.core.provider_retry import call_with_retry
from main_server.core.provider_timeouts import resolve_provider_timeout

_T = TypeVar("_T")


def guard_knowledge(
    operation: str,
    fn: Callable[[], _T],
    *,
    timed: bool = False,
) -> _T:
    try:
        if timed:
            return call_with_retry(
                fn,
                provider="knowledge",
                retryable=(),
                timeout=resolve_provider_timeout("knowledge"),
            )
        return fn()
    except TimeoutError as exc:
        raise KnowledgeTimeoutError(f"{operation}超时") from exc
    except AppError:
        raise
    except Exception as exc:
        raise KnowledgeError(
            f"{operation}失败",
            code="STORAGE_ERROR",
            status_code=500,
        ) from exc
