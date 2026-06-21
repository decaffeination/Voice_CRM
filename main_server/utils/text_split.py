"""文本分句，供流式 TTS 使用。"""

from __future__ import annotations

import re

_SENTENCE_END = re.compile(r"(?<=[。！？!?；;\n])")


def split_sentences(text: str) -> list[str]:
    """按中英文句读切分，保留过短片段合并。"""
    content = text.strip()
    if not content:
        return []

    parts = [part.strip() for part in _SENTENCE_END.split(content) if part.strip()]
    if not parts:
        return [content]

    merged: list[str] = []
    buffer = ""
    for part in parts:
        buffer += part
        if len(buffer) >= 4 or part[-1] in "。！？!?；;":
            merged.append(buffer)
            buffer = ""
    if buffer:
        if merged:
            merged[-1] += buffer
        else:
            merged.append(buffer)
    return merged
