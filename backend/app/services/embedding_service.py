"""
Embedding generation and storage.

Design rule: embedding failure never blocks saving a memory. If the
model is unreachable, the memory is stored unembedded and picked up
by a later backfill. Memories are the asset; vectors are derived and
can always be regenerated.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import get_provider
from app.models import EMBEDDING_DIM, Memory, MemoryEmbedding

# How much text from each attached file goes into the embedding. The
# model only reads roughly the first 250 words of its input anyway;
# keyword search still covers the full extracted text.
ATTACHMENT_TEXT_CHARS = 1500


def _build_source_text(memory: Memory) -> str:
    """
    The text we actually embed.

    Title, topics, content — plus text read from attached files, so a
    question about what's INSIDE a file can find the memory it belongs to.
    """
    parts = [memory.title]
    if memory.topics:
        parts.append(" ".join(memory.topics))
    parts.append(memory.content)

    for attachment in memory.attachments or []:
        if attachment.extracted_text:
            parts.append(
                f"[{attachment.original_filename}]\n"
                f"{attachment.extracted_text[:ATTACHMENT_TEXT_CHARS]}"
            )

    return "\n".join(parts)


def _fit_dimensions(vector: list[float]) -> list[float]:
    """
    Force a vector to the column's dimension.

    Needed only for providers that return a different size (the mock).
    A real model returns exactly EMBEDDING_DIM and this is a no-op.
    """
    if len(vector) == EMBEDDING_DIM:
        return vector
    if len(vector) > EMBEDDING_DIM:
        return vector[:EMBEDDING_DIM]
    return vector + [0.0] * (EMBEDDING_DIM - len(vector))


def embed_memory(db: Session, memory: Memory) -> MemoryEmbedding | None:
    """
    Generate and store an embedding for one memory.

    Returns None on failure rather than raising — a model outage must
    not prevent a memory from being saved.
    """
    provider = get_provider()
    source_text = _build_source_text(memory)

    try:
        raw_vector = provider.embed(source_text)
    except Exception:
        return None

    if not raw_vector:
        return None

    # Replace any existing vector from this model, so re-embedding
    # updates rather than duplicating.
    existing = db.execute(
        select(MemoryEmbedding).where(
            MemoryEmbedding.memory_id == memory.id,
            MemoryEmbedding.model == provider.name,
        )
    ).scalars().all()
    for row in existing:
        db.delete(row)

    embedding = MemoryEmbedding(
        memory_id=memory.id,
        model=provider.name,
        vector=_fit_dimensions(raw_vector),
        source_text=source_text,
    )
    db.add(embedding)
    db.commit()
    db.refresh(embedding)
    return embedding


def backfill_embeddings(db: Session, *, limit: int = 500) -> dict:
    """
    Embed memories that have no vector from the current model.

    Idempotent — safe to run repeatedly. Needed after a model change,
    or after any period when the provider was unreachable.
    """
    provider = get_provider()

    embedded_ids = set(
        db.execute(
            select(MemoryEmbedding.memory_id).where(MemoryEmbedding.model == provider.name)
        ).scalars().all()
    )

    memories = db.execute(select(Memory).limit(limit)).scalars().all()
    pending = [m for m in memories if m.id not in embedded_ids]

    succeeded = 0
    failed = 0
    for memory in pending:
        if embed_memory(db, memory) is not None:
            succeeded += 1
        else:
            failed += 1

    return {
        "provider": provider.name,
        "already_embedded": len(embedded_ids),
        "attempted": len(pending),
        "succeeded": succeeded,
        "failed": failed,
    }


def embedding_status(db: Session) -> dict:
    """How much of the memory store is currently searchable."""
    provider = get_provider()
    total = len(db.execute(select(Memory.id)).scalars().all())
    embedded = len(
        db.execute(
            select(MemoryEmbedding.memory_id).where(MemoryEmbedding.model == provider.name)
        ).scalars().all()
    )
    return {
        "provider": provider.name,
        "provider_available": provider.is_available(),
        "total_memories": total,
        "embedded": embedded,
        "missing": total - embedded,
    }