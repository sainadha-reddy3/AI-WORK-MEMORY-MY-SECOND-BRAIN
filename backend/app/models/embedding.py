"""
Embeddings — the vectors that make semantic search possible.

Kept in a separate table from `memories` deliberately:

  * embedding models change, and dimensions change with them
  * vectors are large, and listing memories shouldn't carry them
  * memories are the asset; embeddings are derived and regenerable

Recording which model produced each vector means a future model
migration can proceed gradually rather than all at once.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# nomic-embed-text produces 768-dimensional vectors.
# This must match the model exactly.
EMBEDDING_DIM = 768


class MemoryEmbedding(Base):
    __tablename__ = "memory_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Which model produced this vector. Without it, a model change
    # would silently mix incompatible vectors.
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    vector: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=False
    )

    # The exact text that was embedded. Kept so a vector can always
    # be traced back to what produced it.
    source_text: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memory: Mapped["Memory"] = relationship(back_populates="embeddings")  # noqa: F821

    def __repr__(self) -> str:
        return f"<MemoryEmbedding {self.model}>"