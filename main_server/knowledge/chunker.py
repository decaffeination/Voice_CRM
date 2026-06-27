from __future__ import annotations

import re

from main_server.config.settings import get_settings
from main_server.core.exceptions import KnowledgeError

_HEADING_PATTERN = re.compile(r"(?m)(?=^#{1,3}\s+)")
_PARAGRAPH_PATTERN = re.compile(r"\n\s*\n+")


def _split_sections(text: str) -> list[str]:
    """按标题与段落边界预切分，便于保留语义单元。"""
    parts: list[str] = []
    for heading_block in _HEADING_PATTERN.split(text):
        block = heading_block.strip()
        if not block:
            continue
        for paragraph in _PARAGRAPH_PATTERN.split(block):
            paragraph = paragraph.strip()
            if paragraph:
                parts.append(paragraph)
    return parts or [text.strip()]


def _chunk_by_size(text: str, size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [c for c in chunks if c]


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    """按段落/标题边界 + 字符窗口切分，保留 overlap。"""
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
    for section in _split_sections(text):
        if len(section) <= size:
            chunks.append(section)
        else:
            chunks.extend(_chunk_by_size(section, size, overlap))
    return chunks


def chunk_documents(documents: list[dict]) -> list[dict]:
    """将解析后的文档切块，保留 metadata。"""
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
