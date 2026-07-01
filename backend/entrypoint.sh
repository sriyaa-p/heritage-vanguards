#!/bin/sh
set -e

echo "==> [entrypoint] Running database migrations..."
alembic upgrade head

echo "==> [entrypoint] Fetching latest UNESCO World Heritage dataset..."
# Graceful: if the fetch fails (network issue, missing script), skip seeding rather than crashing the container
if python /scripts/fetch_unesco_data.py; then
  echo "==> [entrypoint] Seeding UNESCO sites dataset (upsert mode)..."
  python /scripts/seed_database.py
else
  echo "==> [entrypoint] WARNING: fetch_unesco_data.py failed — skipping seed. Using existing dataset."
fi

echo "==> [entrypoint] Starting Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
