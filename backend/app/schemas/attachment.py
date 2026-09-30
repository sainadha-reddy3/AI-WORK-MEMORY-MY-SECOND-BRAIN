"""Schemas for uploaded files."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.memory import MemoryRead


class AttachmentRead(BaseModel):
    id: uuid.UUID
    memory_id: uuid.UUID | None
    kind: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: datetime
    extraction_method: str | None = None
    extraction_confidence: float | None = None
    text_confirmed: bool = False

    class Config:
        from_attributes = True


class UploadResult(BaseModel):
    attachment: AttachmentRead
    memory: MemoryRead


class AttachmentText(BaseModel):
    """The text read from a file, with how it was obtained."""

    id: uuid.UUID
    original_filename: str
    kind: str
    content_type: str
    extraction_method: str | None
    extraction_confidence: float | None
    text_confirmed: bool
    text: str | None


class ConfirmText(BaseModel):
    """The user's reviewed version of a file's text."""

    text: str = Field(max_length=200_000)