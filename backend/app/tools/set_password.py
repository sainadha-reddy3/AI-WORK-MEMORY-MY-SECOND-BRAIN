"""
Set (or change) your login password.

    docker exec -it awm-backend python -m app.tools.set_password

Writes two settings to backend/.auth.env (inside the repo, gitignored by
the cleanup step) so they can be appended to .env without copy-pasting.
The password itself is never printed or stored — only its hash.
"""

import getpass
import secrets
import sys
from pathlib import Path

from app.core.security import hash_password

MIN_LENGTH = 10
OUTPUT = Path("/app/.auth.env")  # = backend/.auth.env on the host


def main() -> None:
    first = getpass.getpass("New password (typing is hidden): ")
    if len(first) < MIN_LENGTH:
        print(f"Too short — use at least {MIN_LENGTH} characters. Nothing was changed.")
        sys.exit(1)
    if getpass.getpass("Same password again: ") != first:
        print("They didn't match. Nothing was changed.")
        sys.exit(1)

    OUTPUT.write_text(
        f"AUTH_PASSWORD_HASH='{hash_password(first)}'\n"
        f"SESSION_SECRET='{secrets.token_urlsafe(48)}'\n"
    )
    print()
    print("✅ Saved to backend/.auth.env. Now, from the repo root, run:")
    print("   cat backend/.auth.env >> .env && rm backend/.auth.env")


if __name__ == "__main__":
    main()