"""领域异常（纯 Python，不依赖 FastAPI）。"""

from __future__ import annotations


class AppError(Exception):
    """业务异常基类。"""

    code: str = "APP_ERROR"
    status_code: int = 400

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
    ):
        self.message = message
        self.code = code or self.__class__.code
        self.status_code = (
            status_code if status_code is not None else self.__class__.status_code
        )
        super().__init__(message)


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404

    def __init__(self, message: str = "资源不存在"):
        super().__init__(message)


class AuthError(AppError):
    code = "AUTH_ERROR"
    status_code = 401

    def __init__(self, message: str = "认证失败"):
        super().__init__(message)


class PermissionDeniedError(AppError):
    code = "PERMISSION_DENIED"
    status_code = 403

    def __init__(self, message: str = "无权访问"):
        super().__init__(message)


class ForbiddenError(PermissionDeniedError):
    """兼容别名，新代码请使用 PermissionDeniedError。"""

    code = "FORBIDDEN"

    def __init__(self, message: str = "无权访问"):
        super().__init__(message)


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 400

    def __init__(self, message: str = "参数校验失败"):
        super().__init__(message)


class ConfigError(AppError):
    code = "CONFIG_ERROR"
    status_code = 500

    def __init__(self, message: str):
        super().__init__(message)


class InternalServerError(AppError):
    code = "INTERNAL_ERROR"
    status_code = 500

    def __init__(self, message: str = "服务内部错误"):
        super().__init__(message)


class CRMError(AppError):
    code = "CRM_ERROR"
    status_code = 400


class KnowledgeError(AppError):
    code = "KNOWLEDGE_ERROR"
    status_code = 400


class KnowledgeTimeoutError(KnowledgeError):
    code = "KNOWLEDGE_TIMEOUT"
    status_code = 504

    def __init__(self, message: str = "知识库操作超时"):
        super().__init__(message, code="KNOWLEDGE_TIMEOUT", status_code=504)


class MemoryError(AppError):
    """记忆存储领域异常（与 Python 内置 MemoryError 区分，请从本模块导入）。"""

    code = "MEMORY_ERROR"
    status_code = 500

    def __init__(self, message: str = "记忆存储操作失败"):
        super().__init__(message)


class ProviderError(AppError):
    """外部 Provider 调用失败。"""

    code = "PROVIDER_ERROR"
    status_code = 502

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        code: str | None = None,
        status_code: int | None = None,
    ):
        self.provider = provider
        super().__init__(message, code=code, status_code=status_code)


class ProviderTimeoutError(ProviderError):
    """Provider 调用超时。"""

    code = "PROVIDER_TIMEOUT"
    status_code = 504


class ProviderConnectionError(ProviderError):
    """Provider 网络连接失败。"""

    code = "PROVIDER_CONNECTION_ERROR"
    status_code = 502


class LLMError(ProviderError):
    code = "LLM_ERROR"

    def __init__(self, message: str, *, provider: str = ""):
        super().__init__(message, provider=provider, code="LLM_ERROR")


class LLMTimeoutError(ProviderTimeoutError):
    def __init__(self, message: str = "LLM 调用超时", *, provider: str = ""):
        super().__init__(message, provider=provider, code="LLM_TIMEOUT", status_code=504)


class LLMConnectionError(ProviderConnectionError):
    def __init__(self, message: str = "LLM 连接失败", *, provider: str = ""):
        super().__init__(
            message, provider=provider, code="LLM_CONNECTION_ERROR", status_code=502
        )


class ASRError(ProviderError):
    code = "ASR_ERROR"

    def __init__(self, message: str, *, provider: str = ""):
        super().__init__(message, provider=provider, code="ASR_ERROR")


class ASRTimeoutError(ProviderTimeoutError):
    def __init__(self, message: str = "ASR 识别超时", *, provider: str = ""):
        super().__init__(message, provider=provider, code="ASR_TIMEOUT", status_code=504)


class TTSError(ProviderError):
    code = "TTS_ERROR"

    def __init__(self, message: str, *, provider: str = ""):
        super().__init__(message, provider=provider, code="TTS_ERROR")


class TTSTimeoutError(ProviderTimeoutError):
    def __init__(self, message: str = "TTS 合成超时", *, provider: str = ""):
        super().__init__(message, provider=provider, code="TTS_TIMEOUT", status_code=504)


class TTSConnectionError(ProviderConnectionError):
    def __init__(self, message: str = "TTS 连接失败", *, provider: str = ""):
        super().__init__(
            message, provider=provider, code="TTS_CONNECTION_ERROR", status_code=502
        )


class ExternalServiceError(LLMError):
    """兼容别名，表示 LLM 外部服务不可用。"""

    code = "EXTERNAL_SERVICE_ERROR"

    def __init__(self, message: str, *, provider: str = ""):
        super().__init__(message, provider=provider)
        self.code = "EXTERNAL_SERVICE_ERROR"


class PipelineError(AppError):
    """Pipeline 阶段处理失败。"""

    code = "PIPELINE_ERROR"
    status_code = 500

    def __init__(self, message: str = "处理失败", *, stage: str = ""):
        self.stage = stage
        super().__init__(message)
