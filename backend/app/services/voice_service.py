"""
Speech to text, running locally with faster-whisper.

Audio never leaves this container. Transcription itself stores
nothing — a recording only becomes part of your memory when you save
it, after seeing (and correcting) the transcript.

Two safeguards keep transcripts honest:

  * segments the model is unsure of are marked [?like this?]
  * if the text comes out in the wrong writing system — a known
    weakness of Whisper with Telugu, which it often writes in
    Devanagari — it is converted letter by letter when the scripts are
    related, and the conversion is reported. If they aren't related,
    the whole transcript is marked uncertain instead.
"""

import io
import math
import unicodedata
from functools import lru_cache

from app.core.config import settings

SUPPORTED_LANGUAGES = {"en", "te", "hi"}

# Below this average log-probability a segment is treated as unclear.
UNCLEAR_LOGPROB = -1.0
# Above this, Whisper thinks the segment probably isn't speech at all.
NO_SPEECH_PROB = 0.6

# Indian scripts share one layout: the same letter sits at the same
# offset inside each 128-character block. That's what makes a
# deterministic conversion between them possible.
INDIC_BLOCKS = {
    "devanagari": 0x0900,  # Hindi
    "bengali": 0x0980,
    "gurmukhi": 0x0A00,
    "gujarati": 0x0A80,
    "oriya": 0x0B00,
    "tamil": 0x0B80,
    "telugu": 0x0C00,
    "kannada": 0x0C80,
    "malayalam": 0x0D00,
}

# Danda punctuation is shared by all these scripts; never shift it.
SHARED_MARKS = {0x0964, 0x0965}

EXPECTED_SCRIPT = {"te": "telugu", "hi": "devanagari"}


@lru_cache(maxsize=1)
def _model():
    """Load Whisper once and keep it in memory."""
    from faster_whisper import WhisperModel

    return WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")


def _dominant_script(text: str) -> str | None:
    """Which Indian script most of the letters belong to, if any."""
    counts: dict[str, int] = {}
    for ch in text:
        code = ord(ch)
        if code in SHARED_MARKS:
            continue
        for name, base in INDIC_BLOCKS.items():
            if base <= code < base + 0x80:
                counts[name] = counts.get(name, 0) + 1
                break
    return max(counts, key=counts.get) if counts else None


def convert_script(text: str, source: str, target: str) -> str:
    """
    Convert text between two Indian scripts, letter by letter.

    Characters with no equivalent in the target script are left as
    they are, so nothing is silently invented.
    """
    src, dst = INDIC_BLOCKS[source], INDIC_BLOCKS[target]
    out: list[str] = []

    # NFD splits combined letters (e.g. Devanagari letters with a dot
    # below) into base + mark, so each part maps cleanly.
    for ch in unicodedata.normalize("NFD", text):
        code = ord(ch)
        if src <= code < src + 0x80 and code not in SHARED_MARKS:
            # Devanagari's nukta (dot below) has no use in Telugu.
            if source == "devanagari" and code == 0x093C:
                continue
            mapped = chr(code - src + dst)
            out.append(mapped if unicodedata.name(mapped, None) else ch)
        else:
            out.append(ch)

    return unicodedata.normalize("NFC", "".join(out))


def transcribe(data: bytes, language: str | None = None) -> dict:
    """
    Turn recorded audio into text.

    `language` may be "en", "te" or "hi"; anything else means
    auto-detect. Silence is filtered out first, which stops Whisper
    from "hearing" phrases in quiet audio.
    """
    if language not in SUPPORTED_LANGUAGES:
        language = None

    # Careful decoding for languages the model has seen less of.
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

    # Check the writing system against the language — the one asked
    # for, or the one Whisper detected when the selector was on Auto.
    target_language = language or (info.language if info.language in SUPPORTED_LANGUAGES else None)
    expected = EXPECTED_SCRIPT.get(target_language or "")
    found = _dominant_script(text)

    script_converted = None
    script_mismatch = False
    if expected and found and found != expected:
        if found in INDIC_BLOCKS and expected in INDIC_BLOCKS:
            text = convert_script(text, found, expected)
            script_converted = f"{found}→{expected}"
        else:
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
        "script_converted": script_converted,
        "model": settings.whisper_model,
    }