"""领域异常类单元测试。"""

from __future__ import annotations

import pytest

from main_server.core.exceptions import (
    ASRError,
    ASRTimeoutError,
    AppError,
    AuthError,
    CRMError,
    ExternalServiceError,
    ForbiddenError,
    InternalServerError,
    KnowledgeError,
    KnowledgeTimeoutError,
    LLMConnectionError,
    LLMError,
    LLMTimeoutError,
    MemoryError,
    NotFoundError,
    PermissionDeniedError,
    PipelineError,
    ProviderConnectionError,
    ProviderError,
    ProviderTimeoutError,
    TTSConnectionError,
    TTSError,
    TTSTimeoutError,
    ValidationError,
)


class TestAppErrorBase:
    def test_default_fields(self) -> None:
        # 场景：默认 AppError；输入：仅 message；预期：默认 code/status
        err = AppError("通用错误")
        assert err.message == "通用错误"
        assert err.code == "APP_ERROR"
        assert err.status_code == 400

    def test_custom_code_and_status(self) -> None:
        # 场景：自定义 code/status；输入：code=CUSTOM, status=418；预期：字段正确
        err = AppError("自定义", code="CUSTOM", status_code=418)
        assert err.code == "CUSTOM"
        assert err.status_code == 418


class TestBuiltinSubclasses:
    @pytest.mark.parametrize(
        "cls,code,status_code",
        [
            (NotFoundError, "NOT_FOUND", 404),
            (AuthError, "AUTH_ERROR", 401),
            (PermissionDeniedError, "PERMISSION_DENIED", 403),
            (ValidationError, "VALIDATION_ERROR", 400),
            (InternalServerError, "INTERNAL_ERROR", 500),
            (MemoryError, "MEMORY_ERROR", 500),
            (PipelineError, "PIPELINE_ERROR", 500),
        ],
    )
    def test_defaults(self, cls, code: str, status_code: int) -> None:
        # 场景：内置异常默认值；输入：无参构造；预期：code/status 符合约定
        err = cls()
        assert err.code == code
        assert err.status_code == status_code
        assert err.message

    def test_forbidden_is_permission_alias(self) -> None:
        # 场景：ForbiddenError 别名；输入：无；预期：继承 PermissionDeniedError
        err = ForbiddenError()
        assert isinstance(err, PermissionDeniedError)
        assert err.code == "FORBIDDEN"


class TestDomainErrors:
    def test_crm_error_overrides(self) -> None:
        # 场景：CRM 自定义状态；输入：404 NOT_FOUND；预期：status_code=404
        err = CRMError("客户不存在", code="NOT_FOUND", status_code=404)
        assert err.code == "NOT_FOUND"
        assert err.status_code == 404

    def test_provider_error_chain(self) -> None:
        # 场景：Provider 异常链；输入：LLMTimeoutError；预期：走 ProviderTimeoutError 分支
        err = LLMTimeoutError("超时", provider="deepseek")
        assert isinstance(err, ProviderTimeoutError)
        assert isinstance(err, ProviderError)
        assert err.provider == "deepseek"
        assert err.code == "LLM_TIMEOUT"
        assert not isinstance(err, LLMError)
        assert not isinstance(err, ExternalServiceError)

    def test_asr_tts_timeout(self) -> None:
        # 场景：ASR/TTS 超时；输入：超时异常；预期：provider 字段保留
        asr_err = ASRTimeoutError("ASR 超时", provider="funasr")
        tts_err = TTSTimeoutError("TTS 超时", provider="edge-tts")
        assert asr_err.provider == "funasr"
        assert tts_err.provider == "edge-tts"

    def test_connection_errors(self) -> None:
        # 场景：连接异常；输入：LLM/TTS 连接失败；预期：code 正确
        llm_conn = LLMConnectionError("连接失败", provider="deepseek")
        tts_conn = TTSConnectionError("连接失败", provider="edge-tts")
        assert isinstance(llm_conn, ProviderConnectionError)
        assert isinstance(tts_conn, ProviderConnectionError)

    def test_knowledge_timeout(self) -> None:
        # 场景：知识库超时；输入：KnowledgeTimeoutError；预期：继承 KnowledgeError
        err = KnowledgeTimeoutError("检索超时")
        assert isinstance(err, KnowledgeError)
