# syntax=docker/dockerfile:1

# --- Stage 1: build the Vue SPA -------------------------------------------------
FROM node:24.11.1-alpine AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: FastAPI app serving /api and the built SPA -------------------------
FROM python:3.13.9-slim AS app

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first so they are cached across source changes.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY backend/ ./
RUN uv sync --locked --no-dev

COPY --from=frontend /frontend/dist ./static

RUN useradd --system --uid 10001 --no-create-home tracker
USER tracker

ENV PATH="/app/.venv/bin:$PATH" \
    STATIC_DIR=/app/static

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"]

# Bring the schema up to date, then serve.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn tracker.app:app --host 0.0.0.0 --port 8000"]
