"""
Core memory tables.

Two tables, deliberately:

  memories  — what the user did or learned
  evidence  — where each memory came from

The split is what makes "never invent the user's history"
enforceable. A memory with no evidence is a memory the system
must not present as fact.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # The date the work actually happened. Not the same as created_at:
    # Wednesday's entry may describe Monday's work.
    occurred_on: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)

    # The cleaned, structured version of what happened.
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # note | learning | mistake | solution | incident | code | meeting
    memory_type: Mapped[str] = mapped_column(
        String(50), default="note", index=True, nullable=False
    )

    # "confirmed" or "uncertain".
    # If the user says "I think I did X", this stays "uncertain"
    # and the system must never present it as fact.
    confidence: Mapped[str] = mapped_column(
        String(20), default="confirmed", nullable=False
    )

    # Free-form tags, e.g. ["argocd", "helm", "gitops"].
    topics: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )

    project: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # en | te | hi | mixed
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # The user's ORIGINAL words, exactly as given.
    # AI processing writes to `content`; this is never overwritten,
    # so there is always a way back to what was actually said.
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)

    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="memory", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Memory {self.occurred_on} {self.title!r}>"


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # user_typed | user_voice | screenshot | document
    # | notebook_photo | meeting_transcript
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # File path, meeting timestamp, or a short note about the origin.
    source_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The specific fragment that supports this memory.
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memory: Mapped["Memory"] = relationship(back_populates="evidence")

    def __repr__(self) -> str:
        return f"<Evidence {self.source_type}>"