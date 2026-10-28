"""
File storage — where original files live.

The rest of the app talks only to this interface, so where files are
kept is a configuration choice, not a code change:

  * LocalStorage — a folder (./storage, mounted into the container)
  * S3Storage    — any S3-compatible service: Neon Object Storage now,
                   Floci's emulated S3 in the lab, real AWS S3 later

Keys look like attachments/YYYY/MM/<uuid>/<filename> in both.
"""

import hashlib
import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path, PurePath

from app.core.config import settings


class StorageBackend(ABC):
    name: str

    @abstractmethod
    def save(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def read(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def list_keys(self) -> list[str]: ...


class LocalStorage(StorageBackend):
    """Files in a folder on disk."""

    name = "local"

    def __init__(self, root: str) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        # Never allow a key like "../../etc/passwd" to escape the folder.
        if self.root.resolve() not in path.parents:
            raise ValueError("Invalid storage key.")
        return path

    def save(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def list_keys(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(
            str(p.relative_to(self.root))
            for p in self.root.rglob("*")
            if p.is_file() and not p.name.startswith(".")
        )


class S3Storage(StorageBackend):
    """Files in an S3-compatible bucket."""

    name = "s3"

    def __init__(self, endpoint: str, bucket: str, access_key: str, secret_key: str, region: str) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint or None,  # None = real AWS
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(
                # Address buckets as https://endpoint/bucket/key — what
                # Neon and most S3-compatible services expect.
                s3={"addressing_style": "path"},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    def save(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)

    def read(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def list_keys(self) -> list[str]:
        keys: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
        return sorted(keys)


def make_s3_storage() -> S3Storage:
    """Build an S3 backend from settings, failing clearly if any are missing."""
    missing = [
        name
        for name, value in {
            "S3_BUCKET": settings.s3_bucket,
            "S3_ACCESS_KEY": settings.s3_access_key,
            "S3_SECRET_KEY": settings.s3_secret_key,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"S3 storage is selected but not configured: {', '.join(missing)}")
    return S3Storage(
        settings.s3_endpoint,
        settings.s3_bucket,
        settings.s3_access_key,
        settings.s3_secret_key,
        settings.s3_region,
    )


@lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    """The storage backend chosen in config."""
    if settings.storage_backend == "s3":
        return make_s3_storage()
    return LocalStorage(settings.storage_dir)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def sha256_of(data: bytes) -> str:
    """Fingerprint of the exact bytes."""
    return hashlib.sha256(data).hexdigest()


def safe_filename(filename: str) -> str:
    """A filename safe for storage keys and download headers."""
    name = PurePath(filename or "file").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).lstrip(".")
    return name[:150] or "file"


def build_key(filename: str) -> str:
    """Where a new upload is stored: attachments/YYYY/MM/<uuid>/<filename>."""
    now = datetime.now(timezone.utc)
    return f"attachments/{now:%Y/%m}/{uuid.uuid4().hex}/{safe_filename(filename)}"