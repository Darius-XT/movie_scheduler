ARG PYTHON_BASE_IMAGE=public.ecr.aws/docker/library/python:3.11-slim
FROM ${PYTHON_BASE_IMAGE}

WORKDIR /app

COPY backend/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --default-timeout=120 \
    "alembic>=1.18.4" \
    "apscheduler>=3.10.0" \
    "beautifulsoup4>=4.13.5" \
    "colorlog>=6.8.0" \
    "fastapi>=0.121.3" \
    "fonttools>=4.63.0" \
    "pydantic>=2.0.0" \
    "playwright>=1.58.0,<2" \
    "requests>=2.31.0" \
    "sqlalchemy>=2.0.0" \
    "urllib3>=2.0.0" \
    "uvicorn>=0.38.0"

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ARG DEBIAN_MIRROR=https://mirrors.aliyun.com
RUN sed -i "s|http://deb.debian.org|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources \
    && python -m playwright install --with-deps --no-shell chromium

COPY backend /app

ENV PYTHONPATH=/app/src

CMD ["uvicorn", "movie_scheduler.app:app", "--host", "0.0.0.0", "--port", "8000"]
