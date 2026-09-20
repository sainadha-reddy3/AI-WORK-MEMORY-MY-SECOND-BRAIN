"""
API schemas for memories.

These describe what the API accepts and returns — deliberately
separate from the database models in app/models/memory.py.

The database model can change without breaking the API contract,
and the API can change without requiring a migration.
"""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

# Allowed values, declared once and reused.
# Literal means anything else is rejected automatically.
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

    class Config:
        from_attributes = True  # allows reading directly from an ORM object


class MemoryCreate(BaseModel):
    """
    What the client sends to create a memory.

    No id and no created_at — the server generates those.
    """

    occurred_on: date
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)

    memory_type: MemoryType = "note"

    # Defaults to "confirmed", but the caller can mark a memory
    # uncertain when the user said "I think..." or "I'm not sure".
    confidence: Confidence = "confirmed"

    topics: list[str] = Field(default_factory=list)
    project: str | None = None
    language: Language = "en"

    # The user's original words. Preserved unchanged so there is
    # always a way back to what was actually said.
    raw_input: str | None = None

    # At least one source should back every memory.
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

    class Config:
        from_attributes = True