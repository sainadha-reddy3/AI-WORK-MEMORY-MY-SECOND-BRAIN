#!/usr/bin/env bash
# Back up everything personal: the database (on Neon) and all original files.
#
#   ./scripts/backup.sh
#
# Creates backups/<timestamp>/ with:
#   database.dump    full Postgres dump (custom format)
#   storage.tar.gz   every original file: screenshots, notebook photos, voice notes
#   SHA256SUMS       fingerprints, so a damaged copy is detected before restoring
#
# backups/ is gitignored — personal data never goes to GitHub.

set -euo pipefail
cd "$(dirname "$0")/.."

set -a; source .env; set +a
: "${NEON_DATABASE_URL:?NEON_DATABASE_URL is not set in .env}"

# Tools must be at least as new as the server (Neon runs Postgres 18).
PGIMAGE="pgvector/pgvector:pg18"
pg() { docker run --rm -i --network host "$PGIMAGE" "$@"; }

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="backups/$STAMP"
mkdir -p "$OUT"

echo "→ Dumping database from Neon..."
pg pg_dump -Fc "$NEON_DATABASE_URL" > "$OUT/database.dump"

echo "→ Archiving original files..."
docker exec awm-backend sh -c 'tar -czf - -C /app/storage .' > "$OUT/storage.tar.gz"

echo "→ Recording fingerprints..."
( cd "$OUT" && sha256sum database.dump storage.tar.gz > SHA256SUMS )

MEMORIES=$(pg psql "$NEON_DATABASE_URL" -tAc "SELECT count(*) FROM memories")
FILES=$(pg psql "$NEON_DATABASE_URL" -tAc "SELECT count(*) FROM attachments")

echo
echo "✅ Backup complete: $OUT"
echo "   memories: $MEMORIES   files: $FILES"
du -sh "$OUT"/* | sed 's/^/   /'
echo
echo "⚠️  This backup is still on the Codespace disk."
echo "   Download the folder to your own computer (Explorer → right-click → Download)."