"""FastAPI 全局异常处理器（传输层）。"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from main_server.core.context import get_request_id
from main_server.core.exceptions import AppError, InternalServerError
from main_server.core.logger import logger


def build_error_body(
    *,
    code: str,
    message: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "success": False,
        "code": code,
        "message": message,
        "request_id": get_request_id(),
    }
    if extra:
        body.update(extra)
    return body


async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_body(code=exc.code, message=exc.message),
    )


async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        body = build_error_body(
            code=str(detail["code"]),
            message=str(detail["message"]),
        )
    elif isinstance(detail, str):
        body = build_error_body(code="HTTP_ERROR", message=detail)
    else:
        body = build_error_body(code="HTTP_ERROR", message="请求失败")
    return JSONResponse(status_code=exc.status_code, content=body)


async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception request_id=%s", get_request_id())
    internal = InternalServerError()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_error_body(code=internal.code, message=internal.message),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)
