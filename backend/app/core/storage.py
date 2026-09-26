"""
File storage abstraction.

Original files (screenshots, notebook photos, documents) live in
storage; the database only keeps a pointer and metadata.

Behind an interface so the backend can change — today a local folder,
later free S3-compatible object storage — without touching any code
that saves or reads files.
"""

import hashlib
import os
import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


class StorageBackend(ABC):
    name: str = "base"

    @abstractmethod
    def save(self, key: str, data: bytes) -> None:
        """Store bytes under a key."""

    @abstractmethod
    def read(self, key: str) -> bytes:
        """Return the bytes stored under a key."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Is anything stored under this key?"""


class LocalStorage(StorageBackend):
    """Stores files in a folder mounted from the host."""

    name = "local"

    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        # Refuse any key that would escape the storage folder.
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError("Invalid storage key")
        return path

    def save(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file then rename, so a crash mid-write never
        # leaves a half-written original behind.
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


@lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    return LocalStorage(settings.storage_dir)


def sha256_of(data: bytes) -> str:
    """Fingerprint of the exact bytes — for de-duplication and backup checks."""
    return hashlib.sha256(data).hexdigest()


def safe_filename(name: str) -> str:
    """Strip path parts and unsafe characters from an uploaded filename."""
    name = os.path.basename(name or "file")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name[:120] or "file"


def build_key(filename: str) -> str:
    """
    attachments/2026/09/<uuid>/<filename>

    Date folders keep it browsable by hand; the uuid prevents two
    uploads with the same name from colliding.
    """
    now = datetime.now(timezone.utc)
    return f"attachments/{now:%Y/%m}/{uuid.uuid4()}/{safe_filename(filename)}"