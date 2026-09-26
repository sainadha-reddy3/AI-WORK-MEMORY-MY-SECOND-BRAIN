"""
Attachments — original files linked to memories.

The file itself lives in storage; this row records what it is, where
it is, and a fingerprint of its exact bytes.

memory_id uses ON DELETE SET NULL: deleting a memory never deletes
the original file behind it.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    memory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # screenshot | image | document | code | notebook_photo
    kind: Mapped[str] = mapped_column(String(30), nullable=False)

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Fingerprint of the exact bytes.
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Which backend holds it, and under what key.
    storage_backend: Mapped[str] = mapped_column(String(30), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)

    # Text pulled out of the file (Task 7.4, OCR in Phase 8).
    # Always a derivative — the original file is the source of truth.
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memory: Mapped["Memory | None"] = relationship(back_populates="attachments")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Attachment {self.kind} {self.original_filename}>"