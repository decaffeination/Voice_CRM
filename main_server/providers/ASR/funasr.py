from __future__ import annotations

import time
from pathlib import Path

from main_server.config.settings import get_settings
from main_server.core.exceptions import ValidationError
from main_server.core.logger import logger
from main_server.core.provider_errors import raise_asr_error
from main_server.core.provider_retry import call_with_retry
from main_server.providers.ASR.base import BaseASR
from main_server.utils.download_asr_model import ensure_asr_model_local

_PROVIDER = "funasr"


class FunASRProvider(BaseASR):
    def __init__(self) -> None:
        from funasr import AutoModel

        settings = get_settings()
        weights_path = ensure_asr_model_local()
        model_dir = weights_path.parent
        device = settings.models.asr.device
        logger.info("加载 FunASR 模型: %s, device=%s", model_dir, device)
        self._model = AutoModel(
            model=str(model_dir),
            device=device,
            disable_update=True,
        )

    def transcribe(self, audio_path: str | Path) -> str:
        path = Path(audio_path)
        if not path.exists():
            raise ValidationError(f"音频文件不存在: {path}")

        audio_duration_s = _audio_duration_seconds(path)
        start = time.perf_counter()

        def _generate():
            return self._model.generate(
                input=str(path),
                cache={},
                language="auto",
                use_itn=True,
                batch_size_s=60,
            )

        try:
            result = call_with_retry(
                _generate,
                provider=_PROVIDER,
                retryable=(),
            )
        except Exception as exc:
            raise_asr_error(exc, provider=_PROVIDER)

        duration_ms = (time.perf_counter() - start) * 1000
        if not result:
            logger.info(
                "asr.transcribe provider=%s duration_ms=%.1f audio_duration_s=%s text_len=0",
                _PROVIDER,
                duration_ms,
                _fmt_duration(audio_duration_s),
            )
            return ""
        from funasr.utils.postprocess_utils import rich_transcription_postprocess

        raw_text = result[0].get("text", "")
        text = rich_transcription_postprocess(raw_text).strip()
        logger.info(
            "asr.transcribe provider=%s duration_ms=%.1f audio_duration_s=%s text_len=%s",
            _PROVIDER,
            duration_ms,
            _fmt_duration(audio_duration_s),
            len(text),
        )
        return text


def _audio_duration_seconds(path: Path) -> float | None:
    try:
        if path.suffix.lower() == ".wav":
            import wave

            with wave.open(str(path), "rb") as wf:
                return wf.getnframes() / float(wf.getframerate())
        import librosa

        return float(librosa.get_duration(path=str(path)))
    except Exception:
        return None


def _fmt_duration(seconds: float | None) -> str:
    return f"{seconds:.2f}" if seconds is not None else "-"


def get_asr_provider() -> BaseASR:
    """兼容别名；请优先使用 ``main_server.providers.registry.get_asr_provider``。"""
    from main_server.providers.registry import get_asr_provider as _get_asr_provider

    return _get_asr_provider()
