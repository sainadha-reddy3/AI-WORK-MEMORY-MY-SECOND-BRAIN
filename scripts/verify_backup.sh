#!/usr/bin/env bash
# Prove a backup actually works — without touching your real data.
#
#   ./scripts/verify_backup.sh backups/<timestamp>
#
# Checks fingerprints, starts a throwaway Postgres 18 server, restores the
# backup into it, counts what came back, then deletes the throwaway server.

set -euo pipefail
cd "$(dirname "$0")/.."

DIR="${1:?Usage: ./scripts/verify_backup.sh backups/<timestamp>}"
PGIMAGE="pgvector/pgvector:pg18"
NAME="awm-verify"

echo "→ Checking fingerprints..."
( cd "$DIR" && sha256sum -c SHA256SUMS )

echo "→ Starting a throwaway Postgres 18 server..."
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" -e POSTGRES_PASSWORD=verify "$PGIMAGE" >/dev/null
trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 30); do
  docker exec "$NAME" pg_isready -U postgres >/dev/null 2>&1 && break
  sleep 1
done

echo "→ Restoring into it..."
docker exec -i "$NAME" pg_restore -U postgres -d postgres --no-owner --no-acl < "$DIR/database.dump"

RESTORED=$(docker exec "$NAME" psql -U postgres -tAc "SELECT count(*) FROM memories")

echo "→ Checking the file archive opens..."
ARCHIVED=$(tar -tzf "$DIR/storage.tar.gz" | grep -vc '/$' || true)

echo
echo "✅ Backup verified: $DIR"
echo "   memories in backup: $RESTORED"
echo "   files in archive:   $ARCHIVED"