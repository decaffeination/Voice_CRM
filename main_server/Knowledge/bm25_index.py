"""BM25 关键词检索索引（从 Chroma 语料构建，供 hybrid 检索使用）。"""

from __future__ import annotations

import math
import re
from functools import lru_cache
from typing import Any

from main_server.Knowledge.storage_guard import guard_knowledge
from main_server.Knowledge.vector_store import get_vector_store
from main_server.core.logger import logger


def tokenize(text: str) -> list[str]:
    """中文单字/双字 + 英文词切分。"""
    lowered = text.lower()
    tokens: list[str] = []
    tokens.extend(re.findall(r"[a-z0-9]+", lowered))
    chars = re.findall(r"[\u4e00-\u9fff]", lowered)
    tokens.extend(chars)
    for index in range(len(chars) - 1):
        tokens.append(chars[index] + chars[index + 1])
    return tokens


class BM25Index:
    """轻量 Okapi BM25，无第三方依赖。"""

    def __init__(
        self,
        documents: list[dict[str, Any]],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self._docs = documents
        self._k1 = k1
        self._b = b
        self._corpus = [tokenize(doc.get("content", "")) for doc in documents]
        self._doc_len = [len(tokens) for tokens in self._corpus]
        total_len = sum(self._doc_len)
        self._avgdl = total_len / len(self._corpus) if self._corpus else 0.0
        self._df: dict[str, int] = {}
        for tokens in self._corpus:
            for term in set(tokens):
                self._df[term] = self._df.get(term, 0) + 1
        self._n = len(self._corpus)

    def search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        if not self._docs or top_k <= 0:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, int]] = []
        for doc_idx, tokens in enumerate(self._corpus):
            score = self._score_document(query_tokens, tokens, self._doc_len[doc_idx])
            if score > 0:
                scored.append((score, doc_idx))

        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, doc_idx in scored[:top_k]:
            doc = dict(self._docs[doc_idx])
            doc["bm25_score"] = round(score, 4)
            results.append(doc)
        return results

    def _score_document(
        self, query_tokens: list[str], doc_tokens: list[str], doc_len: int
    ) -> float:
        if not doc_tokens or self._n == 0:
            return 0.0

        term_freq: dict[str, int] = {}
        for token in doc_tokens:
            term_freq[token] = term_freq.get(token, 0) + 1

        score = 0.0
        for term in query_tokens:
            if term not in term_freq:
                continue
            df = self._df.get(term, 0)
            idf = math.log(1 + (self._n - df + 0.5) / (df + 0.5))
            tf = term_freq[term]
            denom = tf + self._k1 * (
                1 - self._b + self._b * doc_len / max(self._avgdl, 1.0)
            )
            score += idf * tf * (self._k1 + 1) / denom
        return score


def _build_index() -> tuple[BM25Index | None, int]:
    def _load() -> tuple[BM25Index | None, int]:
        store = get_vector_store()
        count = store.count()
        if count == 0:
            return None, 0
        documents = store.fetch_all()
        logger.info("BM25 索引构建 corpus_size=%s", len(documents))
        return BM25Index(documents), count

    return guard_knowledge("构建 BM25 索引", _load)


@lru_cache
def _cached_index(version: int) -> tuple[BM25Index | None, int]:
    return _build_index()


def get_bm25_index() -> BM25Index | None:
    store = get_vector_store()
    version = store.count()
    index, _ = _cached_index(version)
    return index


def invalidate_bm25_cache() -> None:
    _cached_index.cache_clear()


def bm25_search(query: str, top_k: int) -> list[dict[str, Any]]:
    index = get_bm25_index()
    if index is None:
        return []
    return index.search(query, top_k)
