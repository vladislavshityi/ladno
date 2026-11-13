FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY assets ./assets
COPY data ./data
COPY templates ./templates
COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --system --uid 10001 --home-dir /app ladno \
    && mkdir -p /app/uploads \
    && chown ladno /app/uploads
USER ladno

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/api/health')"
# Миграции и сид справочников идемпотентны: выполняются перед каждым стартом.
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
