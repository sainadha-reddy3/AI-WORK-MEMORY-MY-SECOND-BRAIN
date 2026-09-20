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

from app.models import Evidence, Memory
from app.schemas import MemoryCreate


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
        stmt = stmt.where(Memory.topics.contains([topic.strip().lower()]))

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