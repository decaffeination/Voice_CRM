from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor

from main_server.config.settings import get_settings
from main_server.core.exceptions import ValidationError
from main_server.core.logger import logger
from main_server.providers import bootstrap as _providers_bootstrap  # noqa: F401
from main_server.providers.registry import get_tts_provider
from main_server.utils.text_split import split_sentences


async def synthesize_async(text: str, voice: str | None = None) -> bytes:
    content = text.strip()
    if not content:
        raise ValidationError("TTS 文本不能为空")
    settings = get_settings()
    voice_name = voice or settings.models.tts.voice
    provider_name = settings.models.tts.provider
    logger.info(
        "tts.request provider=%s voice=%s text_len=%s",
        provider_name,
        voice_name,
        len(content),
    )
    audio_bytes = await get_tts_provider().synthesize(content, voice_name)
    logger.info(
        "tts.response provider=%s voice=%s audio_bytes=%s",
        provider_name,
        voice_name,
        len(audio_bytes) if audio_bytes else 0,
    )
    return audio_bytes


async def synthesize_sentences_async(
    text: str,
    voice: str | None = None,
) -> AsyncIterator[tuple[int, str, bytes]]:
    """按句合成 TTS，逐句 yield (index, sentence, audio_bytes)。"""
    sentences = split_sentences(text)
    if not sentences:
        return

    for index, sentence in enumerate(sentences):
        audio_bytes = await synthesize_async(sentence, voice=voice)
        yield index, sentence, audio_bytes


def synthesize(text: str, voice: str | None = None) -> bytes:
    """同步 TTS，供脚本调用；FastAPI 路由请用 synthesize_async。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(synthesize_async(text, voice))

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, synthesize_async(text, voice)).result()
