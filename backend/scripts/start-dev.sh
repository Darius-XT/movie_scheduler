#!/bin/sh
set -eu

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting backend dev server..."
exec uvicorn movie_scheduler.app:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/src
