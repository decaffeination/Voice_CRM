"""CRM 存储层异常守卫。"""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import TypeVar

from sqlalchemy.orm import Session

from main_server.DB import db_session
from main_server.core.exceptions import AppError, CRMError

_T = TypeVar("_T")


def guard_crm(operation: str, fn: Callable[[], _T]) -> _T:
    try:
        return fn()
    except AppError:
        raise
    except Exception as exc:
        raise CRMError(
            f"{operation}失败",
            code="STORAGE_ERROR",
            status_code=500,
        ) from exc


@contextmanager
def crm_db_session() -> Generator[Session, None, None]:
    """CRM 专用数据库会话，将底层存储异常转为 CRMError。"""
    try:
        with db_session() as session:
            yield session
    except AppError:
        raise
    except Exception as exc:
        raise CRMError(
            "数据库操作失败",
            code="STORAGE_ERROR",
            status_code=500,
        ) from exc
