"""Schemas for uploaded files."""

import uuid
from datetime import datetime

from pydantic import BaseModel

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

    class Config:
        from_attributes = True


class UploadResult(BaseModel):
    attachment: AttachmentRead
    memory: MemoryRead