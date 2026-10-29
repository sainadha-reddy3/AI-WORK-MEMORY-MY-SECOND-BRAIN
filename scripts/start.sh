#!/usr/bin/env bash
# Start the whole app.
#
#   ./scripts/start.sh
#
# Uses the backend image already on disk if there is one. If it's
# missing (e.g. after a Codespace restart), pulls the prebuilt image
# from GitHub Container Registry — giving up after 5 minutes and
# building locally instead. Then starts the containers and runs the
# frontend in this terminal. Ctrl+C stops the frontend.
#
# The backend code is mounted live, so an older image still runs the
# latest code. Only dependency changes need a fresh image:
#   docker pull ghcr.io/sainadha-reddy3/ai-work-memory-my-second-brain/backend:latest

set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE="ghcr.io/sainadha-reddy3/ai-work-memory-my-second-brain/backend:latest"

if docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "→ Backend image already on disk — skipping download."
else
  echo "→ Backend image missing — pulling the prebuilt one (up to 5 minutes)..."
  if ! timeout 300 docker pull "$IMAGE"; then
    echo "→ Pull didn't finish — building locally instead..."
    docker compose build backend
  fi
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