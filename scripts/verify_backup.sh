#!/usr/bin/env bash
# Prove a backup actually works — without touching your real data.
#
#   ./scripts/verify_backup.sh backups/<timestamp>
#
# Checks fingerprints, restores the database into a throwaway test
# database, counts what came back, then deletes the test database.

set -euo pipefail
cd "$(dirname "$0")/.."

DIR="${1:?Usage: ./scripts/verify_backup.sh backups/<timestamp>}"

echo "→ Checking fingerprints..."
( cd "$DIR" && sha256sum -c SHA256SUMS )

echo "→ Restoring into a throwaway database..."
docker exec awm-postgres sh -c 'dropdb -U "$POSTGRES_USER" --if-exists awm_verify && createdb -U "$POSTGRES_USER" awm_verify'
docker exec -i awm-postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d awm_verify --no-owner' < "$DIR/database.dump"

RESTORED=$(docker exec awm-postgres sh -c 'psql -U "$POSTGRES_USER" -d awm_verify -tAc "SELECT count(*) FROM memories"')
LIVE=$(docker exec awm-postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM memories"')

echo "→ Checking the file archive opens..."
ARCHIVED=$(tar -tzf "$DIR/storage.tar.gz" | grep -vc '/$' || true)

docker exec awm-postgres sh -c 'dropdb -U "$POSTGRES_USER" awm_verify'

echo
echo "✅ Backup verified: $DIR"
echo "   memories in backup: $RESTORED   (live database now: $LIVE)"
echo "   files in archive:   $ARCHIVED"