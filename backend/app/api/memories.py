"""
Memory API endpoints.

Thin HTTP layer. All real logic lives in app/services — these
functions only translate between HTTP and the service layer.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import (
    CaptureResult,
    EvidenceCreate,
    MemoryCapture,
    MemoryCreate,
    MemoryRead,
)
from app.services import (
    MemoryValidationError,
    capture_memory,
    create_memory,
    get_memory,
    list_memories,
)

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
def create(data: MemoryCreate, db: Session = Depends(get_db)):
    """
    Create a memory with explicit fields.

    The precise path — used for imports, tests, and any case needing
    exact control. For natural language, use /memories/capture.
    """
    if not data.evidence:
        data.evidence = [
            EvidenceCreate(source_type="user_typed", excerpt=data.content[:500])
        ]

    try:
        return create_memory(db, data)
    except MemoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


@router.post(
    "/capture", response_model=CaptureResult, status_code=status.HTTP_201_CREATED
)
def capture(data: MemoryCapture, db: Session = Depends(get_db)):
    """
    Create a memory from natural language.

    The user writes freely; the AI proposes title, type and topics.
    The response includes what was inferred, so nothing is applied
    invisibly.

    Declared BEFORE /{memory_id} — otherwise FastAPI would try to
    parse "capture" as a UUID.
    """
    try:
        memory, preview = capture_memory(db, data)
        return {"memory": memory, "preview": preview}
    except MemoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


@router.get("", response_model=list[MemoryRead])
def list_all(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    topic: str | None = None,
    memory_type: str | None = None,
    since: date | None = None,
    until: date | None = None,
):
    """
    List memories, newest work first.

    These filters back the left panel (Today / This Week) and
    topic-centric history later on.
    """
    return list_memories(
        db,
        limit=limit,
        offset=offset,
        topic=topic,
        memory_type=memory_type,
        since=since,
        until=until,
    )


@router.get("/{memory_id}", response_model=MemoryRead)
def get_one(memory_id: uuid.UUID, db: Session = Depends(get_db)):
    """Fetch a single memory with its evidence."""
    memory = get_memory(db, memory_id)
    if memory is None:
        # 404 rather than an empty response: the system should never
        # imply it has a memory it doesn't have.
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory