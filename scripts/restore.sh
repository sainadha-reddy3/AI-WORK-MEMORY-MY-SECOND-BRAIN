#!/usr/bin/env bash
# Replace the current database and files with a backup.
#
#   ./scripts/restore.sh backups/<timestamp>
#
# Safety: verifies fingerprints, asks you to type RESTORE, and takes a
# fresh backup of the current state first — so even a mistaken restore
# can be undone.

set -euo pipefail
cd "$(dirname "$0")/.."

DIR="${1:?Usage: ./scripts/restore.sh backups/<timestamp>}"

echo "→ Checking fingerprints..."
( cd "$DIR" && sha256sum -c SHA256SUMS )

echo
echo "This REPLACES your current memories and files with the backup in:"
echo "   $DIR"
read -r -p "Type RESTORE to continue: " ANSWER
if [ "$ANSWER" != "RESTORE" ]; then
  echo "Cancelled. Nothing was changed."
  exit 1
fi

echo "→ Backing up the current state first..."
./scripts/backup.sh

echo "→ Restoring database..."
docker exec -i awm-postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < "$DIR/database.dump"

echo "→ Restoring original files..."
docker exec -i awm-backend sh -c 'rm -rf /app/storage/* && tar -xzf - -C /app/storage' < "$DIR/storage.tar.gz"

echo
echo "✅ Restored from $DIR"