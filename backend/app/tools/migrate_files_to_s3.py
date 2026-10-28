"""
One-time move of existing files from the local folder into S3 storage.

For each file: verify its fingerprint locally, upload it under the same
key, read it back and verify again, and only then mark the record as
stored in S3. Local copies are left in place as a safety net.

Safe to rerun — records already marked "s3" are skipped.

    docker exec awm-backend python -m app.tools.migrate_files_to_s3
"""

from sqlalchemy import select

from app.core.config import settings
from app.core.storage import LocalStorage, make_s3_storage, sha256_of
from app.db.session import SessionLocal
from app.models import Attachment


def main() -> None:
    local = LocalStorage(settings.storage_dir)
    s3 = make_s3_storage()
    db = SessionLocal()

    rows = db.execute(
        select(Attachment).where(Attachment.storage_backend == "local")
    ).scalars().all()

    uploaded: set[str] = set()
    moved = 0
    problems = 0

    for attachment in rows:
        key = attachment.storage_key

        # Identical files share one stored copy — upload each key once.
        if key not in uploaded:
            if not local.exists(key):
                print(f"MISSING locally, skipped: {key}")
                problems += 1
                continue

            data = local.read(key)
            if sha256_of(data) != attachment.sha256:
                print(f"FINGERPRINT MISMATCH locally, skipped: {key}")
                problems += 1
                continue

            s3.save(key, data)

            if sha256_of(s3.read(key)) != attachment.sha256:
                print(f"UPLOAD VERIFY FAILED, skipped: {key}")
                problems += 1
                continue

            uploaded.add(key)
            print(f"uploaded and verified: {key}")

        attachment.storage_backend = "s3"
        moved += 1

    db.commit()
    db.close()

    print()
    print(f"records moved: {moved}   files uploaded: {len(uploaded)}   problems: {problems}")


if __name__ == "__main__":
    main()