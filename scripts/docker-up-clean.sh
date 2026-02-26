#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "[error] Docker Compose is not installed." >&2
  exit 1
fi

echo "[1/5] Stopping existing Docker stack..."
"${COMPOSE_CMD[@]}" down --remove-orphans || true

echo "[2/5] Killing old local dev processes (vite/uvicorn)..."
pkill -f "vite --host" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true

echo "[3/5] Removing stale project containers if any..."
for container in ai-frontend ai-backend ai-redis; do
  docker rm -f "$container" 2>/dev/null || true
done

echo "[4/5] Rebuilding images with no cache..."
"${COMPOSE_CMD[@]}" build --no-cache

echo "[5/5] Starting fresh stack..."
"${COMPOSE_CMD[@]}" up -d

echo
"${COMPOSE_CMD[@]}" ps

echo
echo "Done. Verify endpoints:"
echo "- Frontend: http://localhost:5173"
echo "- Backend:  http://localhost:8000"
