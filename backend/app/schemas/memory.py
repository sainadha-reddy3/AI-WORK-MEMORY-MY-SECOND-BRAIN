"""
API schemas for memories.

These describe what the API accepts and returns — deliberately
separate from the database models in app/models/memory.py.
"""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

MemoryType = Literal[
    "note", "learning", "mistake", "solution", "incident", "code", "meeting"
]

Confidence = Literal["confirmed", "uncertain"]

SourceType = Literal[
    "user_typed",
    "user_voice",
    "screenshot",
    "document",
    "notebook_photo",
    "meeting_transcript",
]

Language = Literal["en", "te", "hi", "mixed"]


class EvidenceCreate(BaseModel):
    """One source backing a memory."""

    source_type: SourceType
    source_detail: str | None = None
    excerpt: str | None = None


class EvidenceRead(EvidenceCreate):
    id: uuid.UUID
    created_at: datetime
    # Set when the evidence is an uploaded file.
    attachment_id: uuid.UUID | None = None

    class Config:
        from_attributes = True


class AttachmentBrief(BaseModel):
    """
    Compact view of a file attached to a memory.

    Defined here rather than in schemas/attachment.py because that
    module imports MemoryRead — defining it there would be circular.
    """

    id: uuid.UUID
    kind: str
    original_filename: str
    content_type: str
    size_bytes: int

    class Config:
        from_attributes = True


class MemoryCreate(BaseModel):
    """What the client sends to create a memory with explicit fields."""

    occurred_on: date
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)
    memory_type: MemoryType = "note"
    confidence: Confidence = "confirmed"
    topics: list[str] = Field(default_factory=list)
    project: str | None = None
    language: Language = "en"
    raw_input: str | None = None
    evidence: list[EvidenceCreate] = Field(default_factory=list)


class MemoryRead(BaseModel):
    """What the API returns when reading a memory."""

    id: uuid.UUID
    occurred_on: date
    created_at: datetime
    title: str
    content: str
    memory_type: str
    confidence: str
    topics: list[str]
    project: str | None
    language: str
    raw_input: str | None
    evidence: list[EvidenceRead]
    attachments: list[AttachmentBrief] = Field(default_factory=list)

    class Config:
        from_attributes = True


class MemoryCapture(BaseModel):
    """
    Natural-language memory capture.

    The user writes freely; the AI proposes structure. Only `text`
    is required — everything else is optional override.
    """

    text: str = Field(min_length=1)
    occurred_on: date | None = None
    project: str | None = None
    topics: list[str] | None = None


class CapturePreview(BaseModel):
    """What the AI proposed, shown so nothing is applied invisibly."""

    provider: str
    ai_available: bool
    title: str
    memory_type: str
    confidence: str
    topics: list[str]
    language: str
    uncertainty_markers: list[str]


class CaptureResult(BaseModel):
    memory: MemoryRead
    preview: CapturePreview