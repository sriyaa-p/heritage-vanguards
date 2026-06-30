#!/bin/sh
set -e

echo "==> [entrypoint] Running database migrations..."
alembic upgrade head

echo "==> [entrypoint] Fetching latest UNESCO World Heritage dataset..."
python /scripts/fetch_unesco_data.py

echo "==> [entrypoint] Seeding UNESCO sites dataset (upsert mode)..."
python /scripts/seed_database.py

echo "==> [entrypoint] Starting Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
