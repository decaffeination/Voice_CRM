from __future__ import annotations

from main_server.config.settings import get_settings
from main_server.core.exceptions import KnowledgeError


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    """按字符切分文本。"""
    settings = get_settings()
    size = chunk_size or settings.knowledge.chunk_size
    overlap = chunk_overlap or settings.knowledge.chunk_overlap
    if size <= 0:
        raise KnowledgeError(
            "chunk_size 必须大于 0", code="VALIDATION_ERROR", status_code=400
        )
    if overlap >= size:
        overlap = max(0, size // 5)

    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [c for c in chunks if c]


def chunk_documents(documents: list[dict]) -> list[dict]:
    """将解析后的文档切块，保留 metadata。"""
    settings = get_settings()
    results: list[dict] = []
    for doc_index, doc in enumerate(documents):
        metadata = dict(doc.get("metadata") or {})
        for chunk_index, chunk in enumerate(
            chunk_text(doc.get("content", ""))
        ):
            item_metadata = {
                **metadata,
                "doc_index": doc_index,
                "chunk_index": chunk_index,
            }
            results.append({"content": chunk, "metadata": item_metadata})
    return results
