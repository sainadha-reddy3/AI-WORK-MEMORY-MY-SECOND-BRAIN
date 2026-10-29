#!/usr/bin/env bash
# Start the whole app.
#
#   ./scripts/start.sh
#
# Pulls the prebuilt backend image from GitHub Container Registry
# (fast, and a no-op if it hasn't changed), falls back to building
# locally if the pull fails, starts the containers, then runs the
# frontend in this terminal. Ctrl+C stops the frontend.

set -euo pipefail
cd "$(dirname "$0")/.."

echo "→ Getting the backend image..."
if ! docker compose pull backend; then
  echo "→ Pull failed — building locally instead (~8 minutes)..."
  docker compose build backend
fi

echo "→ Starting database and backend..."
docker compose up -d

echo "→ Waiting for the backend..."
for _ in $(seq 1 60); do
  curl -sf http://localhost:8000/health >/dev/null && break
  sleep 2
done
curl -sf http://localhost:8000/health >/dev/null && echo "   backend is up" || echo "   ⚠️  backend not responding yet — check: docker compose logs backend"

echo "→ Starting the frontend (Ctrl+C to stop it)..."
cd frontend
npm run dev