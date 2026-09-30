"""
Speech to text, running locally with faster-whisper.

Audio never leaves this container. Transcription itself stores
nothing — a recording only becomes part of your memory when you save
it, after seeing (and correcting) the transcript.

Segments the model is unsure of are marked [?like this?]. And if the
output is in the wrong writing system for the language requested
(e.g. Tamil script when Telugu was asked for), the whole transcript is
marked — wrong-language text must never look trustworthy.
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

# Unicode ranges for the scripts we expect.
SCRIPT_RANGES = {
    "telugu": (0x0C00, 0x0C7F),
    "devanagari": (0x0900, 0x097F),  # Hindi
    "tamil": (0x0B80, 0x0BFF),
    "kannada": (0x0C80, 0x0CFF),
    "malayalam": (0x0D00, 0x0D7F),
}
EXPECTED_SCRIPT = {"te": "telugu", "hi": "devanagari"}


@lru_cache(maxsize=1)
def _model():
    """Load Whisper once and keep it in memory."""
    from faster_whisper import WhisperModel

    return WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")


def _dominant_script(text: str) -> str | None:
    """Which non-Latin script most of the letters belong to, if any."""
    counts: dict[str, int] = {}
    for ch in text:
        code = ord(ch)
        for name, (lo, hi) in SCRIPT_RANGES.items():
            if lo <= code <= hi:
                counts[name] = counts.get(name, 0) + 1
                break
    return max(counts, key=counts.get) if counts else None


def transcribe(data: bytes, language: str | None = None) -> dict:
    """
    Turn recorded audio into text.

    `language` may be "en", "te" or "hi"; anything else means
    auto-detect. Silence is filtered out first, which stops Whisper
    from "hearing" phrases in quiet audio.
    """
    if language not in SUPPORTED_LANGUAGES:
        language = None

    # Careful decoding for languages the model has seen less of;
    # fast decoding otherwise.
    beam = 5 if language in {"te", "hi"} else 1

    segments, info = _model().transcribe(
        io.BytesIO(data),
        language=language,
        vad_filter=True,  # skip silence — prevents hallucinated phrases
        beam_size=beam,
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

    text = " ".join(parts).strip()

    # Wrong writing system for the language asked for? Say so.
    script_mismatch = False
    expected = EXPECTED_SCRIPT.get(language or "")
    found = _dominant_script(text)
    if expected and found and found != expected:
        script_mismatch = True
        text = f"[?{text}?]"
        unclear = max(unclear, 1)

    confidence = (
        round(math.exp(sum(logprobs) / len(logprobs)) * 100, 1) if logprobs else None
    )

    return {
        "text": text,
        "language": info.language,
        "language_probability": round(info.language_probability * 100, 1),
        "duration": round(info.duration, 1),
        "confidence": confidence,
        "unclear_segments": unclear,
        "script_mismatch": script_mismatch,
        "model": settings.whisper_model,
    }