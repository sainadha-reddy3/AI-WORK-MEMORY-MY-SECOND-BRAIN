"""
Attachments — original files linked to memories.

The file itself lives in storage; this row records what it is, where
it is, a fingerprint of its exact bytes, and any text read from it.

memory_id uses ON DELETE SET NULL: deleting a memory never deletes
the original file behind it.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, String, Text, func
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

    # Text read from the file. Always a derivative — the original file
    # is the source of truth.
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # How the text was obtained: text | pdf | docx | ocr
    extraction_method: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # OCR's average word confidence (0-100). Null for exact extraction.
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # False until the user has reviewed the text. Unconfirmed OCR is
    # never presented as what the user wrote.
    text_confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memory: Mapped["Memory | None"] = relationship(back_populates="attachments")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Attachment {self.kind} {self.original_filename}>"