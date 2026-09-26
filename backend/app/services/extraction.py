"""
Text extraction from uploaded files.

Everything produced here is DERIVED data — category 2 in the project's
source rules ("extracted from uploaded files"). The original file is
always the source of truth; this text exists so its contents can be
searched.

Images return None on purpose. Reading text out of screenshots and
handwriting is OCR (Phase 8); until then nothing is guessed.
"""

import io
import re
from pathlib import PurePath

# Enough for very long documents without bloating the database.
MAX_CHARS = 200_000

# Patterns that indicate a real credential inside a file's contents.
# Kept deliberately specific, so ordinary notes are never refused.
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),        # SSH / TLS private keys
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                       # AWS access key id
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),             # GitHub tokens
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),           # Slack tokens
    re.compile(r'"type"\s*:\s*"service_account"'),             # GCP service-account key file
    re.compile(r'"private_key"\s*:\s*"-----BEGIN'),            # any JSON-embedded private key
]


def extract_text(data: bytes, filename: str, content_type: str, kind: str) -> str | None:
    """
    Return the readable text inside a file, or None when there is none
    (images, scanned PDFs, unreadable files).

    Never raises — a file whose text can't be read is still stored.
    """
    suffix = PurePath(filename.lower()).suffix

    try:
        if kind == "code" or suffix in {".txt", ".md"} or content_type.startswith("text/"):
            text = data.decode("utf-8", errors="replace")

        elif suffix == ".pdf" or content_type == "application/pdf":
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)

        elif suffix == ".docx":
            import docx

            document = docx.Document(io.BytesIO(data))
            text = "\n".join(p.text for p in document.paragraphs)

        else:
            # Images and anything else: no extraction yet (OCR is Phase 8).
            return None

    except Exception:
        return None

    # Null bytes are not allowed in Postgres text columns.
    text = text.replace("\x00", "").strip()
    return text[:MAX_CHARS] or None


def looks_like_secret(text: str) -> bool:
    """True if the text contains something that looks like a real credential."""
    return any(p.search(text) for p in SECRET_PATTERNS)