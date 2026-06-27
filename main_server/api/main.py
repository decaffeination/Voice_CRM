"""FastAPI 应用入口：组装路由、认证、生命周期。"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from main_server.api.audit_api import router as audit_router
from main_server.api.audio import router as audio_router
from main_server.api.chat import router as chat_router
from main_server.api.crm_api import router as crm_router
from main_server.api.dashboard_api import router as dashboard_router
from main_server.api.knowledge_api import router as knowledge_router
from main_server.api.memory_api import router as memory_router
from main_server.api.session_api import router as session_router
from main_server.api.rbac_api import router as rbac_router
from main_server.api.settings_api import router as settings_router
from main_server.api.user_api import router as user_router
from main_server.api.websocket.audio_ws import router as ws_router
from main_server.core.exception_handlers import register_exception_handlers
from main_server.core.middleware import RequestContextMiddleware
from main_server.core.logger import logger
from main_server.providers import bootstrap as _providers_bootstrap  # noqa: F401
from main_server.services.health_service import get_health_status
from main_server.config.settings import get_settings
from main_server.utils.init_db import init_database
from main_server.utils.startup_checks import warn_startup_config


def _validate_provider_modules() -> None:
    """启动时校验 TTS 实现并刷新 Provider 注册。"""
    import inspect

    from main_server.providers import bootstrap
    from main_server.providers.registry import list_registered_providers
    from main_server.providers.TTS import edge_tts as edge_tts_provider

    bootstrap.refresh_default_providers()

    providers = list_registered_providers()
    if "chattts" not in providers["tts"]:
        raise RuntimeError("chattts provider 未注册")

    module_source = inspect.getsource(edge_tts_provider)
    if "importlib.import_module" not in module_source:
        raise RuntimeError("edge_tts 未使用 importlib 加载 edge_tts SDK")

    logger.info("Provider 模块校验通过: TTS=%s", ", ".join(providers["tts"]))


async def _warmup_asr() -> None:
    """后台预热 ASR 模型，避免首个语音请求承担冷加载。"""
    try:
        from main_server.providers.registry import get_asr_provider

        logger.info("ASR 预热开始")
        await asyncio.to_thread(get_asr_provider)
        logger.info("ASR 预热完成")
    except Exception:  # noqa: BLE001
        logger.exception("ASR 预热失败")


async def _warmup_tts() -> None:
    """后台预热本地 TTS（如 ChatTTS）模型，避免首个请求承担 ~60s 冷加载。

    仅对需要本地权重加载的 provider 生效；云端 provider（edge-tts）跳过。
    预热在独立线程执行，不阻塞服务启动；失败仅记录日志，不影响运行。
    """
    from main_server.config.settings import get_settings

    provider_name = get_settings().models.tts.provider
    if provider_name != "chattts":
        return

    try:
        from main_server.providers.registry import get_tts_provider

        logger.info("TTS 预热开始 provider=%s", provider_name)
        await asyncio.to_thread(get_tts_provider)
        logger.info("TTS 预热完成 provider=%s", provider_name)
    except Exception:  # noqa: BLE001 - 预热失败不应阻断服务
        logger.exception("TTS 预热失败 provider=%s", provider_name)


async def _warmup_providers() -> None:
    """后台并行预热 ASR / TTS，不阻塞服务接受请求。"""
    await asyncio.gather(_warmup_asr(), _warmup_tts(), return_exceptions=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    warn_startup_config()
    init_database()
    _validate_provider_modules()
    logger.info("Voice-CRM 服务启动")
    warmup_task = asyncio.create_task(_warmup_providers())
    try:
        yield
    finally:
        warmup_task.cancel()
        logger.info("Voice-CRM 服务关闭")


app = FastAPI(title="Voice-CRM", lifespan=lifespan)
register_exception_handlers(app)

_cors = get_settings().cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors.resolved_origins,
    allow_credentials=_cors.allow_credentials,
    allow_methods=_cors.allow_methods,
    allow_headers=_cors.allow_headers,
)
app.add_middleware(RequestContextMiddleware)
app.include_router(user_router, prefix="/api")
app.include_router(chat_router)
app.include_router(session_router)
app.include_router(memory_router)
app.include_router(crm_router)
app.include_router(dashboard_router)
app.include_router(knowledge_router)
app.include_router(audit_router)
app.include_router(settings_router)
app.include_router(rbac_router)
app.include_router(audio_router)
app.include_router(ws_router)


@app.get("/health")
def health_check():
    return get_health_status()


def run() -> None:
    """仅启动后端。前端+后端组合请使用项目根目录的 run.py。"""
    from main_server.config.settings import get_settings
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main_server.api.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        reload_dirs=["main_server", "agent"],
    )


if __name__ == "__main__":
    run()
