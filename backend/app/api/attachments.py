"""
Attachment endpoints — upload originals, fetch them back.
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.storage import safe_filename
from app.db.session import get_db
from app.schemas import AttachmentRead, UploadResult
from app.services.attachment_service import (
    MAX_UPLOAD_BYTES,
    AttachmentError,
    get_attachment,
    list_attachments,
    read_attachment,
    upload_attachment,
)

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.post("", response_model=UploadResult, status_code=201)
def upload(
    file: UploadFile = File(...),
    note: str | None = Form(None),
    memory_id: str | None = Form(None),
    kind: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload a file as evidence.

    Optional `note` describes it (becomes an AI-structured memory).
    Optional `memory_id` attaches it to an existing memory instead.
    """
    # Read one byte past the limit, so oversize files are detected
    # without loading an arbitrarily large upload into memory.
    data = file.file.read(MAX_UPLOAD_BYTES + 1)

    try:
        parsed_id = uuid.UUID(memory_id) if memory_id else None
    except ValueError:
        raise HTTPException(status_code=422, detail="memory_id is not a valid id.")

    try:
        attachment, memory = upload_attachment(
            db,
            data=data,
            filename=file.filename or "file",
            content_type=file.content_type or "",
            note=note,
            memory_id=parsed_id,
            kind=kind or None,
        )
    except AttachmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"attachment": attachment, "memory": memory}


@router.get("", response_model=list[AttachmentRead])
def list_all(
    kind: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Recent uploads, optionally filtered by kind."""
    return list_attachments(db, kind=kind, limit=limit)


@router.get("/{attachment_id}", response_model=AttachmentRead)
def metadata(attachment_id: uuid.UUID, db: Session = Depends(get_db)):
    attachment = get_attachment(db, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found.")
    return attachment


@router.get("/{attachment_id}/file")
def download(attachment_id: uuid.UUID, db: Session = Depends(get_db)):
    """Serve the original file exactly as uploaded."""
    attachment = get_attachment(db, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found.")

    try:
        data = read_attachment(attachment)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="The original file is missing from storage.",
        )

    return Response(
        content=data,
        media_type=attachment.content_type,
        headers={
            "Content-Disposition": f'inline; filename="{safe_filename(attachment.original_filename)}"'
        },
    )