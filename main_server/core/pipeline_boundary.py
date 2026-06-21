"""Pipeline 阶段边界：统一打点与异常包装。"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator

from main_server.core.exceptions import AppError, PipelineError
from main_server.core.logger import logger


def _log_stage_start(name: str, session_id: str | None) -> float:
    logger.info(
        "pipeline.stage.start stage=%s session_id=%s",
        name,
        session_id or "-",
    )
    return time.perf_counter()


def _handle_stage_outcome(
    name: str,
    session_id: str | None,
    start: float,
    exc: BaseException | None,
) -> None:
    if exc is None:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "pipeline.stage.end stage=%s session_id=%s duration_ms=%.1f",
            name,
            session_id or "-",
            duration_ms,
        )
        return

    if isinstance(exc, AppError):
        logger.warning(
            "pipeline.stage.error stage=%s session_id=%s",
            name,
            session_id or "-",
            exc_info=True,
        )
        return

    logger.exception(
        "pipeline.stage.failure stage=%s session_id=%s",
        name,
        session_id or "-",
    )


@contextmanager
def pipeline_stage(name: str, *, session_id: str | None = None) -> Iterator[None]:
    start = _log_stage_start(name, session_id)
    exc: BaseException | None = None
    try:
        yield
    except AppError as err:
        exc = err
        raise
    except Exception as err:
        exc = err
        raise PipelineError("处理失败", stage=name) from err
    finally:
        _handle_stage_outcome(name, session_id, start, exc)


@asynccontextmanager
async def async_pipeline_stage(
    name: str, *, session_id: str | None = None
) -> AsyncIterator[None]:
    start = _log_stage_start(name, session_id)
    exc: BaseException | None = None
    try:
        yield
    except AppError as err:
        exc = err
        raise
    except Exception as err:
        exc = err
        raise PipelineError("处理失败", stage=name) from err
    finally:
        _handle_stage_outcome(name, session_id, start, exc)
