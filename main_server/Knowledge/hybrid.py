"""Hybrid 检索：向量 + BM25 结果 RRF 融合。"""

from __future__ import annotations

from typing import Any


def reciprocal_rank_fusion(
    *result_lists: list[dict[str, Any]],
    top_k: int,
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion：合并多路检索结果。"""
    scores: dict[str, float] = {}
    doc_map: dict[str, dict[str, Any]] = {}

    for results in result_lists:
        for rank, doc in enumerate(results):
            doc_id = doc.get("id")
            if not doc_id:
                continue
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank + 1)
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

    if not scores:
        return []

    sorted_ids = sorted(scores, key=lambda doc_id: scores[doc_id], reverse=True)
    merged: list[dict[str, Any]] = []
    for doc_id in sorted_ids[:top_k]:
        item = dict(doc_map[doc_id])
        item["hybrid_score"] = round(scores[doc_id], 4)
        merged.append(item)
    return merged
