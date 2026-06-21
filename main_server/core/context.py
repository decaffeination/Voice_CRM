"""请求上下文（contextvars），供日志与错误响应关联。"""

from __future__ import annotations

import contextvars
from uuid import uuid4

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)
user_id_var: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "user_id", default=None
)
session_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "session_id", default=None
)


def new_request_id() -> str:
    return uuid4().hex[:16]


def get_request_id() -> str:
    return request_id_var.get()
