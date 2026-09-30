"""
Voice endpoint — transcribe a recording without storing it.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.voice_service import transcribe

router = APIRouter(prefix="/voice", tags=["voice"])

MAX_AUDIO_BYTES = 15 * 1024 * 1024  # about 15 minutes of compressed speech


class Transcript(BaseModel):
    text: str
    language: str
    language_probability: float
    duration: float
    confidence: float | None
    unclear_segments: int
    # True when the output is in the wrong writing system for the
    # language requested (e.g. Tamil script when Telugu was asked for).
    script_mismatch: bool = False
    model: str


@router.post("/transcribe", response_model=Transcript)
def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = Form(None),
):
    """
    Transcribe audio. Nothing is stored — the recording only becomes
    part of your memory when you save it afterwards.
    """
    data = file.file.read(MAX_AUDIO_BYTES + 1)
    if not data:
        raise HTTPException(status_code=422, detail="The recording is empty.")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=422, detail="The recording is larger than 15 MB.")

    try:
        return transcribe(data, language or None)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not transcribe this audio: {exc}")