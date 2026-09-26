"""
Attachments — storing original files and linking them to memories.

Rules enforced here:

  * the original file is always kept, byte for byte
  * a file becomes EVIDENCE for its memory, not decoration
  * with no description, nothing about the file's content is invented
  * obvious credential files are refused before they reach storage
"""

import uuid
from datetime import date
from pathlib import PurePath

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.storage import build_key, get_storage, sha256_of
from app.models import Attachment, Evidence, Memory
from app.schemas import EvidenceCreate, MemoryCapture, MemoryCreate
from app.services.embedding_service import embed_memory
from app.services.memory_service import capture_memory, create_memory

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB

VALID_KINDS = {"screenshot", "image", "document", "code", "notebook_photo"}

IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

DOCUMENT_SUFFIXES = {".pdf", ".txt", ".md", ".docx"}

CODE_SUFFIXES = {
    ".py", ".yaml", ".yml", ".tf", ".tfvars", ".hcl", ".json", ".sh",
    ".toml", ".ini", ".conf", ".js", ".ts", ".go", ".sql", ".xml",
}
CODE_FILENAMES = {"dockerfile", "makefile", "jenkinsfile"}

# Files that almost certainly contain credentials. Refused outright —
# this system must never become a place where secrets are stored.
SECRET_FILENAMES = {".env", "id_rsa", "id_ed25519", "credentials.json", ".npmrc", ".pypirc"}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".keystore"}

# How each kind of file is recorded as evidence.
EVIDENCE_SOURCE = {
    "screenshot": "screenshot",
    "image": "screenshot",
    "notebook_photo": "notebook_photo",
    "document": "document",
    "code": "document",
}

KIND_LABEL = {
    "screenshot": "Screenshot",
    "image": "Image",
    "notebook_photo": "Notebook photo",
    "document": "Document",
    "code": "Code file",
}


class AttachmentError(ValueError):
    """Raised when an upload cannot be accepted."""


def classify(filename: str, content_type: str, requested: str | None) -> str:
    """Decide what kind of file this is, refusing unsafe or unknown ones."""
    name = PurePath(filename).name.lower()
    suffix = PurePath(name).suffix

    if name in SECRET_FILENAMES or name.startswith(".env") or suffix in SECRET_SUFFIXES:
        raise AttachmentError(
            "This looks like a credentials file. It was not stored — "
            "secrets must never be kept in your memory system."
        )

    if requested:
        if requested not in VALID_KINDS:
            raise AttachmentError(f"Unknown kind '{requested}'.")
        return requested

    if content_type in IMAGE_TYPES:
        return "screenshot"
    if name in CODE_FILENAMES or suffix in CODE_SUFFIXES:
        return "code"
    if suffix in DOCUMENT_SUFFIXES or content_type in {"application/pdf", "text/plain", "text/markdown"}:
        return "document"

    raise AttachmentError(
        f"Unsupported file type ({content_type or suffix or 'unknown'})."
    )


def _store_file(
    db: Session, data: bytes, filename: str, content_type: str, kind: str
) -> Attachment:
    """Save the bytes (once per unique content) and create the record."""
    if not data:
        raise AttachmentError("The file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise AttachmentError("The file is larger than 15 MB.")

    storage = get_storage()
    digest = sha256_of(data)

    # Same bytes already stored? Reuse them rather than keeping a copy.
    existing = db.execute(
        select(Attachment).where(Attachment.sha256 == digest).limit(1)
    ).scalar_one_or_none()

    if existing is not None and storage.exists(existing.storage_key):
        key = existing.storage_key
    else:
        key = build_key(filename)
        storage.save(key, data)

    attachment = Attachment(
        kind=kind,
        original_filename=filename[:255],
        content_type=content_type or "application/octet-stream",
        size_bytes=len(data),
        sha256=digest,
        storage_backend=storage.name,
        storage_key=key,
    )
    db.add(attachment)
    db.flush()
    return attachment


def upload_attachment(
    db: Session,
    *,
    data: bytes,
    filename: str,
    content_type: str,
    note: str | None = None,
    memory_id: uuid.UUID | None = None,
    kind: str | None = None,
) -> tuple[Attachment, Memory]:
    """
    Store a file and link it to a memory as evidence.

    * memory_id given   → attach to that existing memory
    * note given        → create a memory from the note (AI-structured)
    * neither           → create a minimal memory that describes only
                          the upload itself, never the file's content
    """
    kind = classify(filename, content_type, kind)
    source_type = EVIDENCE_SOURCE[kind]

    existing_memory = None
    if memory_id is not None:
        existing_memory = db.get(Memory, memory_id)
        if existing_memory is None:
            raise AttachmentError("Memory not found.")

    attachment = _store_file(db, data, filename, content_type, kind)
    note = (note or "").strip()

    if existing_memory is not None:
        memory = existing_memory
        db.add(
            Evidence(
                memory_id=memory.id,
                source_type=source_type,
                source_detail=f"Original file: {filename}",
                excerpt=note or None,
                attachment_id=attachment.id,
            )
        )

    elif note:
        # The note becomes a normal AI-structured memory (with its own
        # user_typed evidence); the file is added as a second source.
        memory, _ = capture_memory(db, MemoryCapture(text=note))
        db.add(
            Evidence(
                memory_id=memory.id,
                source_type=source_type,
                source_detail=f"Original file: {filename}",
                excerpt=None,
                attachment_id=attachment.id,
            )
        )

    else:
        # No description: record only that the upload happened.
        label = KIND_LABEL[kind]
        memory = create_memory(
            db,
            MemoryCreate(
                occurred_on=date.today(),
                title=f"{label}: {filename}"[:300],
                content=f"Uploaded {label.lower()} '{filename}' with no description.",
                memory_type="note",
                evidence=[
                    EvidenceCreate(
                        source_type=source_type,
                        source_detail=f"Original file: {filename}",
                    )
                ],
            ),
        )
        memory.evidence[0].attachment_id = attachment.id
        embed_memory(db, memory)

    attachment.memory_id = memory.id
    db.commit()
    db.refresh(attachment)
    db.refresh(memory)
    return attachment, memory


def get_attachment(db: Session, attachment_id: uuid.UUID) -> Attachment | None:
    return db.get(Attachment, attachment_id)


def list_attachments(
    db: Session, *, kind: str | None = None, limit: int = 50
) -> list[Attachment]:
    stmt = select(Attachment).order_by(Attachment.created_at.desc()).limit(limit)
    if kind:
        stmt = stmt.where(Attachment.kind == kind)
    return list(db.execute(stmt).scalars().all())


def read_attachment(attachment: Attachment) -> bytes:
    """
    Return the original bytes.

    Raises FileNotFoundError when storage has lost the file, so the
    caller can say so plainly instead of serving something broken.
    """
    storage = get_storage()
    if not storage.exists(attachment.storage_key):
        raise FileNotFoundError(attachment.storage_key)
    return storage.read(attachment.storage_key)