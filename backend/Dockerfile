FROM python:3.11-slim

WORKDIR /app

COPY backend/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --default-timeout=120 \
    "alembic>=1.18.4" \
    "beautifulsoup4>=4.13.5" \
    "colorlog>=6.8.0" \
    "fastapi>=0.121.3" \
    "pydantic>=2.0.0" \
    "requests>=2.31.0" \
    "sqlalchemy>=2.0.0" \
    "urllib3>=2.0.0" \
    "uvicorn>=0.38.0"

COPY backend /app

ENV PYTHONPATH=/app/src

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
