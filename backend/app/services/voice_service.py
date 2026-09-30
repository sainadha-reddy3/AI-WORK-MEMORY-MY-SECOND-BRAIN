"""
Speech to text, running locally with faster-whisper.

Audio never leaves this container. Transcription itself stores
nothing — a recording only becomes part of your memory when you save
it, after seeing (and correcting) the transcript.

Segments the model is unsure of are marked [?like this?], the same
convention used for OCR, so a transcript never reads more certain
than the model actually was.
"""

import io
import math
from functools import lru_cache

from app.core.config import settings

SUPPORTED_LANGUAGES = {"en", "te", "hi"}

# Below this average log-probability a segment is treated as unclear.
UNCLEAR_LOGPROB = -1.0
# Above this, Whisper thinks the segment probably isn't speech at all.
NO_SPEECH_PROB = 0.6


@lru_cache(maxsize=1)
def _model():
    """Load Whisper once and keep it in memory."""
    from faster_whisper import WhisperModel

    return WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")


def transcribe(data: bytes, language: str | None = None) -> dict:
    """
    Turn recorded audio into text.

    `language` may be "en", "te" or "hi"; anything else means
    auto-detect. Silence is filtered out first, which stops Whisper
    from "hearing" phrases in quiet audio.
    """
    if language not in SUPPORTED_LANGUAGES:
        language = None

    segments, info = _model().transcribe(
        io.BytesIO(data),
        language=language,
        vad_filter=True,  # skip silence — prevents hallucinated phrases
        beam_size=1,      # fastest decoding; plenty for notes
    )

    parts: list[str] = []
    logprobs: list[float] = []
    unclear = 0

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        if segment.avg_logprob < UNCLEAR_LOGPROB or segment.no_speech_prob > NO_SPEECH_PROB:
            parts.append(f"[?{text}?]")
            unclear += 1
        else:
            parts.append(text)
        logprobs.append(segment.avg_logprob)

    confidence = (
        round(math.exp(sum(logprobs) / len(logprobs)) * 100, 1) if logprobs else None
    )

    return {
        "text": " ".join(parts).strip(),
        "language": info.language,
        "language_probability": round(info.language_probability * 100, 1),
        "duration": round(info.duration, 1),
        "confidence": confidence,
        "unclear_segments": unclear,
        "model": settings.whisper_model,
    }