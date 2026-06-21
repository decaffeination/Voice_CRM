"""Provider 异常映射单元测试。"""

from __future__ import annotations

import httpx
import pytest

from main_server.core.exceptions import (
    ASRError,
    ASRTimeoutError,
    LLMConnectionError,
    LLMError,
    LLMTimeoutError,
    TTSConnectionError,
    TTSError,
    TTSTimeoutError,
)
from main_server.core.provider_errors import (
    raise_asr_error,
    raise_llm_error,
    raise_tts_error,
)


class TestRaiseLlmError:
    def test_timeout(self) -> None:
        with pytest.raises(LLMTimeoutError) as exc_info:
            raise_llm_error(httpx.TimeoutException("timeout"), provider="deepseek")
        assert exc_info.value.code == "LLM_TIMEOUT"
        assert exc_info.value.provider == "deepseek"

    def test_connection(self) -> None:
        with pytest.raises(LLMConnectionError) as exc_info:
            raise_llm_error(httpx.ConnectError("refused"), provider="deepseek")
        assert exc_info.value.code == "LLM_CONNECTION_ERROR"

    def test_generic(self) -> None:
        with pytest.raises(LLMError) as exc_info:
            raise_llm_error(httpx.HTTPError("server error"), provider="deepseek")
        assert exc_info.value.code == "LLM_ERROR"


class TestRaiseAsrError:
    def test_timeout(self) -> None:
        with pytest.raises(ASRTimeoutError):
            raise_asr_error(TimeoutError(), provider="funasr")

    def test_generic(self) -> None:
        with pytest.raises(ASRError):
            raise_asr_error(RuntimeError("boom"), provider="funasr")


class TestRaiseTtsError:
    def test_timeout(self) -> None:
        with pytest.raises(TTSTimeoutError):
            raise_tts_error(TimeoutError(), provider="edge-tts")

    def test_connection(self) -> None:
        with pytest.raises(TTSConnectionError):
            raise_tts_error(ConnectionError("network"), provider="edge-tts")

    def test_generic(self) -> None:
        with pytest.raises(TTSError):
            raise_tts_error(ValueError("bad voice"), provider="edge-tts")
