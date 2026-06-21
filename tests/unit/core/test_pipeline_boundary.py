"""Pipeline 异常边界测试。"""

from __future__ import annotations

import asyncio

import pytest

from main_server.core.exceptions import PipelineError, ValidationError
from main_server.core.pipeline_boundary import async_pipeline_stage, pipeline_stage


class TestPipelineStage:
    def test_passes_through_app_error(self) -> None:
        with pytest.raises(ValidationError):
            with pipeline_stage("memory_load", session_id="s1"):
                raise ValidationError("记忆加载失败")

    def test_wraps_unknown_exception(self) -> None:
        with pytest.raises(PipelineError) as exc_info:
            with pipeline_stage("asr", session_id="s1"):
                raise RuntimeError("model crash")
        err = exc_info.value
        assert err.stage == "asr"
        assert err.code == "PIPELINE_ERROR"
        assert err.status_code == 500

    def test_successful_stage(self) -> None:
        with pipeline_stage("tts", session_id="s1"):
            result = "ok"
        assert result == "ok"


class TestAsyncPipelineStage:
    def test_wraps_unknown_exception(self) -> None:
        async def _run() -> None:
            with pytest.raises(PipelineError) as exc_info:
                async with async_pipeline_stage("tts", session_id="s1"):
                    raise ValueError("async failure")
            assert exc_info.value.stage == "tts"

        asyncio.run(_run())

    def test_passes_through_app_error(self) -> None:
        async def _run() -> None:
            with pytest.raises(ValidationError):
                async with async_pipeline_stage("agent_invoke"):
                    raise ValidationError("agent 失败")

        asyncio.run(_run())
