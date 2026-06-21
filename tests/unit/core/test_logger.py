"""应用日志写入验证；live 抽检见 tests/live/scripts/logger_check.py。"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

RUN_TAG = uuid.uuid4().hex[:8]


@dataclass
class LogSlice:
    path: Path
    _offset: int = 0

    def mark(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._offset = self.path.stat().st_size if self.path.exists() else 0

    def read_new(self) -> str:
        if not self.path.exists():
            return ""
        with self.path.open(encoding="utf-8") as fh:
            fh.seek(self._offset)
            return fh.read()

    def assert_exists(self) -> None:
        assert self.path.exists()

    def assert_contains(self, pattern: str, *, hint: str = "") -> None:
        text = self.read_new()
        assert re.search(pattern, text), f"未找到 {pattern!r} ({hint})"

    def assert_has_traceback(self, *, hint: str = "") -> None:
        assert "Traceback (most recent call last):" in self.read_new(), hint


@pytest.fixture
def log_slice() -> LogSlice:
    from main_server.config.settings import get_settings

    return LogSlice(get_settings().logging.abs_file)


def _make_llm():
    from main_server.providers.LLM.deepseek import DeepSeekLLM

    llm = DeepSeekLLM.__new__(DeepSeekLLM)
    llm._api_key = "sk-test"
    llm._base_url = "https://api.deepseek.com"
    llm._model = "deepseek-chat"
    return llm


class TestLogger:
    def test_log_file_generated(self, log_slice: LogSlice) -> None:
        # 场景：日志文件写入；输入：logger.info；预期：文件含标记
        from main_server.core.logger import logger

        log_slice.mark()
        logger.info("logger_test.ping tag=%s", RUN_TAG)
        log_slice.assert_contains(rf"logger_test\.ping tag={RUN_TAG}")

    def test_api_request_log(self, log_slice: LogSlice, memory_db) -> None:
        # 场景：HTTP + api.chat 日志；输入：mock chat；预期：http.request / api.chat
        from main_server.api.chat import router as chat_router
        from main_server.api.user_api import router as user_router
        from main_server.core.auth.permission import Role
        from main_server.services.pipeline.chat_pipeline import ChatPipelineResult
        from tests.conftest import make_test_app, token_for_user

        app = make_test_app(user_router, prefix="/api")
        app.include_router(chat_router)
        log_slice.mark()
        client = TestClient(app)
        token = token_for_user(1, "admin", [Role.ADMIN])

        async def _mock_run(self, actor, user_input, with_audio=False):
            return ChatPipelineResult(
                text="日志测试回复",
                conversation_state={"current_intent": "chitchat"},
                intent="chitchat",
            )

        with patch(
            "main_server.services.pipeline.chat_pipeline.ChatPipeline.run_async",
            _mock_run,
        ):
            resp = client.post(
                "/api/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": f"logger-{RUN_TAG}", "with_audio": False},
            )
        assert resp.status_code == 200
        log_slice.assert_contains(r"api\.chat session_id=")

    def test_agent_route_log(self, log_slice: LogSlice) -> None:
        # 场景：Agent 路由日志；输入：pending_gate；预期：agent.route
        from agent.router import pending_gate_node
        from main_server.config.constants import PENDING_WRITE_AWAITING

        log_slice.mark()
        pending_gate_node(
            {
                "user_input": "确认",
                "conversation_state": {
                    "pending_write": {
                        "type": "followup",
                        "payload": {"content": "测试"},
                        "status": PENDING_WRITE_AWAITING,
                    }
                },
            }
        )
        log_slice.assert_contains(r"agent\.route pending_gate intent=confirm")

    def test_llm_success_log(self, log_slice: LogSlice) -> None:
        # 场景：LLM 成功日志；输入：mock httpx；预期：llm.call + tokens
        log_slice.mark()
        llm = _make_llm()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        }
        mock_response.raise_for_status = MagicMock()
        with patch("main_server.providers.LLM.deepseek.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            llm.chat([{"role": "user", "content": f"logger-llm-{RUN_TAG}"}])
        log_slice.assert_contains(r"llm\.call provider=deepseek")

    def test_llm_failure_log(self, log_slice: LogSlice) -> None:
        # 场景：LLM 失败日志；输入：超时；预期：llm.call_failed + 堆栈
        from main_server.core.exceptions import LLMTimeoutError

        log_slice.mark()
        llm = _make_llm()
        with patch("main_server.providers.LLM.deepseek.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = (
                httpx.TimeoutException("timeout")
            )
            with pytest.raises(LLMTimeoutError):
                llm.chat([{"role": "user", "content": "fail"}])
        log_slice.assert_contains(r"llm\.call_failed provider=deepseek")
        log_slice.assert_has_traceback()

    def test_pipeline_exception_log(self, log_slice: LogSlice) -> None:
        # 场景：Pipeline 异常；输入：stage 内 RuntimeError；预期：pipeline.stage.failure
        from main_server.core.exceptions import PipelineError
        from main_server.core.pipeline_boundary import pipeline_stage

        log_slice.mark()
        marker = f"logger-pipeline-{RUN_TAG}"
        with pytest.raises(PipelineError):
            with pipeline_stage("logger_test", session_id=f"sid-{RUN_TAG}"):
                raise RuntimeError(marker)
        log_slice.assert_contains(r"pipeline\.stage\.failure stage=logger_test")

    def test_http_unhandled_exception_log(self, log_slice: LogSlice) -> None:
        # 场景：HTTP 500；输入：未捕获异常；预期：unhandled_exception
        from main_server.core.exception_handlers import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/logger-boom")
        def _boom() -> None:
            raise RuntimeError(f"logger-http-{RUN_TAG}")

        log_slice.mark()
        client = TestClient(app, raise_server_exceptions=False)
        assert client.get("/logger-boom").status_code == 500
        log_slice.assert_contains(r"unhandled_exception request_id=")
