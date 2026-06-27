from __future__ import annotations

from functools import lru_cache
from typing import Any

from main_server.knowledge.bm25_index import bm25_search, invalidate_bm25_cache
from main_server.knowledge.hybrid import reciprocal_rank_fusion
from main_server.knowledge.storage_guard import guard_knowledge
from main_server.knowledge.vector_store import get_vector_store
from main_server.config.settings import get_settings
from main_server.core.logger import logger
from main_server.utils.hf_model_loader import load_cross_encoder


def search(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    limit = top_k or settings.knowledge.top_k
    rerank_limit = settings.knowledge.rerank_top_k or limit

    def _search() -> list[dict[str, Any]]:
        fetch_k = max(limit, rerank_limit, settings.knowledge.fetch_k)
        if settings.knowledge.hybrid_enabled:
            docs = _hybrid_search(query, fetch_k)
        else:
            docs = _vector_search(query, fetch_k)

        if settings.knowledge.rerank_enabled:
            docs = _rerank(query, docs, rerank_limit)
        else:
            docs = docs[:limit]

        return _filter_by_threshold(docs)

    docs = guard_knowledge("知识库检索", _search)
    top_score = _primary_score(docs[0]) if docs else None
    logger.info(
        "knowledge.search query_len=%s top_k=%s rerank_top_k=%s hit_count=%s top_score=%s "
        "hybrid=%s rerank=%s",
        len(query),
        limit,
        rerank_limit,
        len(docs),
        top_score,
        settings.knowledge.hybrid_enabled,
        settings.knowledge.rerank_enabled,
    )
    return docs


def invalidate_index_cache() -> None:
    """ingest 后刷新 BM25 缓存。"""
    invalidate_bm25_cache()


def _hybrid_search(query: str, fetch_k: int) -> list[dict[str, Any]]:
    vector_docs = _vector_search(query, fetch_k)
    keyword_docs = bm25_search(query, fetch_k)
    if not vector_docs and not keyword_docs:
        return []
    if not vector_docs:
        return keyword_docs
    if not keyword_docs:
        return vector_docs
    return reciprocal_rank_fusion(
        vector_docs,
        keyword_docs,
        top_k=fetch_k,
        rrf_k=get_settings().knowledge.rrf_k,
    )


def _vector_search(query: str, top_k: int) -> list[dict[str, Any]]:
    store = get_vector_store()
    return store.query(query_text=query, top_k=top_k)


def _filter_by_threshold(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    settings = get_settings()
    filtered: list[dict[str, Any]] = []
    for doc in docs:
        rerank_score = doc.get("rerank_score")
        if rerank_score is not None:
            if rerank_score < settings.knowledge.min_rerank_score:
                continue
        else:
            vector_score = doc.get("score")
            if vector_score is not None and vector_score < settings.knowledge.min_vector_score:
                continue
        filtered.append(doc)
    return filtered


def _primary_score(doc: dict[str, Any]) -> float | None:
    if doc.get("rerank_score") is not None:
        return doc["rerank_score"]
    if doc.get("hybrid_score") is not None:
        return doc["hybrid_score"]
    if doc.get("bm25_score") is not None:
        return doc["bm25_score"]
    return doc.get("score")


@lru_cache
def _get_reranker():
    def _load():
        settings = get_settings()
        cache_dir = settings.models.abs_rerank_cache
        cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "加载 Rerank 模型: %s, cache=%s",
            settings.models.rerank.model,
            cache_dir,
        )
        return load_cross_encoder(settings.models.rerank.model, cache_dir)

    return guard_knowledge("加载 Rerank 模型", _load)


def _rerank(
    query: str, docs: list[dict[str, Any]], top_k: int
) -> list[dict[str, Any]]:
    if not docs:
        return []

    reranker = _get_reranker()

    def _run() -> list[dict[str, Any]]:
        pairs = [(query, doc.get("content", "")) for doc in docs]
        scores = reranker.predict(pairs)
        for doc, score in zip(docs, scores):
            doc["rerank_score"] = round(float(score), 4)
        docs.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        return docs[:top_k]

    return guard_knowledge("知识库重排序", _run, timed=True)
