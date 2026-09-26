"""
Memory service — the business logic layer.

Endpoints deal with HTTP. This module deals with meaning:
what a valid memory is, and how memories are retrieved.

Key rule enforced here: a memory must have at least one piece of
evidence. Memories without a traceable source cannot later be
presented as the user's history, so we refuse to create them.
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai import get_provider
from app.models import Evidence, Memory
from app.schemas import EvidenceCreate, MemoryCapture, MemoryCreate


class MemoryValidationError(ValueError):
    """Raised when a memory cannot be accepted as written."""


def create_memory(db: Session, data: MemoryCreate) -> Memory:
    """
    Create a memory and its evidence in a single transaction.

    Refuses memories with no evidence: an untraceable memory cannot
    be used to answer questions about the user's history, so storing
    one would quietly create a gap.
    """
    if not data.evidence:
        raise MemoryValidationError(
            "A memory must have at least one piece of evidence. "
            "Every memory needs a traceable source."
        )

    memory = Memory(
        occurred_on=data.occurred_on,
        title=data.title,
        content=data.content,
        memory_type=data.memory_type,
        confidence=data.confidence,
        topics=[t.strip().lower() for t in data.topics if t.strip()],
        project=data.project,
        language=data.language,
        # Preserve the user's original words. If the caller didn't
        # supply raw_input, fall back to the content as given.
        raw_input=data.raw_input or data.content,
    )

    db.add(memory)
    # flush() sends the INSERT so memory.id is generated, without
    # finalising the transaction.
    db.flush()

    for item in data.evidence:
        db.add(
            Evidence(
                memory_id=memory.id,
                source_type=item.source_type,
                source_detail=item.source_detail,
                excerpt=item.excerpt,
            )
        )

    # Memory and evidence are committed together, or not at all.
    db.commit()
    db.refresh(memory)
    return memory


def get_memory(db: Session, memory_id: uuid.UUID) -> Memory | None:
    """Fetch one memory with its evidence loaded."""
    stmt = (
        select(Memory)
        .where(Memory.id == memory_id)
        .options(selectinload(Memory.evidence))
    )
    return db.execute(stmt).scalar_one_or_none()


def list_memories(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    topic: str | None = None,
    memory_type: str | None = None,
    since: date | None = None,
    until: date | None = None,
) -> list[Memory]:
    """
    List memories, newest work first.

    The filters here are the foundation of the left panel
    (Today / This Week) and of topic-centric history in Phase 6.
    """
    stmt = select(Memory).options(selectinload(Memory.evidence))

    if topic:
        # Postgres array containment: does topics include this tag?
        stmt = stmt.where(Memory.topics.any(topic.strip().lower()))

    if memory_type:
        stmt = stmt.where(Memory.memory_type == memory_type)

    if since:
        stmt = stmt.where(Memory.occurred_on >= since)

    if until:
        stmt = stmt.where(Memory.occurred_on <= until)

    stmt = (
        stmt.order_by(Memory.occurred_on.desc(), Memory.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(db.execute(stmt).scalars().all())


def count_memories(db: Session) -> int:
    """Total memories stored. Used by the UI's counters."""
    return len(list(db.execute(select(Memory.id)).scalars().all()))


def capture_memory(db: Session, data: MemoryCapture) -> tuple[Memory, dict]:
    """
    Create a memory from natural language, with AI-proposed structure.

    The AI proposes; it does not decide. Three invariants hold
    regardless of what the model returns:

      * raw_input keeps the user's exact words
      * uncertainty is never downgraded to certainty
      * the evidence row records that structuring was AI-assisted,
        so inferred fields are distinguishable from stated ones
    """
    provider = get_provider()
    structured = provider.structure_memory(data.text)

    # Explicit user input always wins over AI inference.
    topics = data.topics if data.topics is not None else structured.topics

    memory_in = MemoryCreate(
        occurred_on=data.occurred_on or date.today(),
        title=structured.title,
        # The user's words, not the model's rewrite.
        content=data.text.strip(),
        memory_type=structured.memory_type,
        confidence=structured.confidence,
        topics=topics,
        project=data.project,
        language=structured.language,
        raw_input=data.text.strip(),
        evidence=[
            EvidenceCreate(
                source_type="user_typed",
                source_detail=(
                    f"Structured by AI provider '{provider.name}'. "
                    "Title, type and topics are AI interpretation; "
                    "the content is the user's own words."
                ),
                excerpt=data.text.strip()[:500],
            )
        ],
    )

    memory = create_memory(db, memory_in)

    # Embed for semantic search. Deliberately best-effort: if the
    # model is unreachable the memory is still saved, and a backfill
    # will pick it up later. Imported locally to avoid a circular
    # import with embedding_service.
    from app.services.embedding_service import embed_memory

    embed_memory(db, memory)

    preview = {
        "provider": provider.name,
        "ai_available": provider.is_available(),
        "title": structured.title,
        "memory_type": structured.memory_type,
        "confidence": structured.confidence,
        "topics": topics,
        "language": structured.language,
        "uncertainty_markers": structured.uncertainty_markers,
    }

    return memory, preview