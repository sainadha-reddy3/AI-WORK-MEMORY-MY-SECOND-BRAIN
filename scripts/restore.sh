#!/usr/bin/env bash
# Replace the database on Neon and the local files with a backup.
#
#   ./scripts/restore.sh backups/<timestamp>
#
# Safety: verifies fingerprints, asks you to type RESTORE, and takes a
# fresh backup of the current state first — so even a mistaken restore
# can be undone.

set -euo pipefail
cd "$(dirname "$0")/.."

set -a; source .env; set +a
: "${NEON_DATABASE_URL:?NEON_DATABASE_URL is not set in .env}"

DIR="${1:?Usage: ./scripts/restore.sh backups/<timestamp>}"
PGIMAGE="pgvector/pgvector:pg18"

echo "→ Checking fingerprints..."
( cd "$DIR" && sha256sum -c SHA256SUMS )

echo
echo "This REPLACES your memories on Neon and your local files with:"
echo "   $DIR"
read -r -p "Type RESTORE to continue: " ANSWER
if [ "$ANSWER" != "RESTORE" ]; then
  echo "Cancelled. Nothing was changed."
  exit 1
fi

echo "→ Backing up the current state first..."
./scripts/backup.sh

echo "→ Restoring database to Neon..."
docker run --rm -i --network host "$PGIMAGE" \
  pg_restore --clean --if-exists --no-owner --no-acl -d "$NEON_DATABASE_URL" < "$DIR/database.dump"

echo "→ Restoring original files..."
docker exec -i awm-backend python -m app.tools.files_archive import < "$DIR/storage.tar.gz"
echo
echo "✅ Restored from $DIR"