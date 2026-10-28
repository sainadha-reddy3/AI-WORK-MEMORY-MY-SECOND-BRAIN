"""
Export or import every stored file as a tar.gz stream — works with any
storage backend (local folder or S3), so backups follow the files.

    python -m app.tools.files_archive export > files.tar.gz
    python -m app.tools.files_archive import < files.tar.gz
"""

import io
import sys
import tarfile
import time

from app.core.storage import get_storage


def export_files(out) -> None:
    storage = get_storage()
    count = 0
    with tarfile.open(fileobj=out, mode="w|gz") as tar:
        for key in storage.list_keys():
            data = storage.read(key)
            info = tarfile.TarInfo(name=key)
            info.size = len(data)
            info.mtime = int(time.time())
            tar.addfile(info, io.BytesIO(data))
            count += 1
    print(f"exported {count} files", file=sys.stderr)


def import_files(inp) -> None:
    storage = get_storage()
    count = 0
    with tarfile.open(fileobj=inp, mode="r|gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            name = member.name[2:] if member.name.startswith("./") else member.name
            parts = name.split("/")
            # Refuse anything that could escape the storage area, and skip hidden files.
            if name.startswith("/") or ".." in parts or parts[-1].startswith("."):
                continue
            storage.save(name, tar.extractfile(member).read())
            count += 1
    print(f"imported {count} files", file=sys.stderr)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "export":
        export_files(sys.stdout.buffer)
    elif command == "import":
        import_files(sys.stdin.buffer)
    else:
        print("usage: python -m app.tools.files_archive export|import", file=sys.stderr)
        sys.exit(2)