"""预加载知识库相关模型，避免首条检索在推理阶段冷启动。"""

from __future__ import annotations

from main_server.Knowledge.retriever import _get_reranker
from main_server.Knowledge.vector_store import get_vector_store
from main_server.config.settings import get_settings
from main_server.core.logger import logger


def warmup_knowledge_models() -> None:
    settings = get_settings()
    logger.info("预热知识库模型: vector_store (含 embedding)")
    get_vector_store()
    if settings.knowledge.rerank_enabled:
        logger.info("预热知识库模型: rerank")
        _get_reranker()
    logger.info("知识库模型预热完成")
