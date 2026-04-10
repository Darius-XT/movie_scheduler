#!/bin/sh
set -eu

echo "开始执行 Alembic 迁移..."
alembic upgrade head

echo "启动后端开发服务..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/src
