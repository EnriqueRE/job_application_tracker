# Backend

FastAPI + SQLAlchemy 2.0 (sync) + psycopg 3 + Alembic, managed with [uv](https://docs.astral.sh/uv/).
The Python package is `tracker` (in `src/tracker/`). All HTTP routes live under `/api`.

## Setup

```sh
cd backend
uv sync
```

## Configuration

Settings are read from environment variables (or a `backend/.env` file) by
`tracker.settings.Settings`:

| Variable       | Required | Example                                                |
| -------------- | -------- | ------------------------------------------------------ |
| `DATABASE_URL` | yes      | `postgresql+psycopg://tracker:secret@localhost:5432/tracker` |
| `STATIC_DIR`   | no       | `../frontend/dist`                                     |

When `STATIC_DIR` is set (the Docker image sets it), the app also serves that built SPA:
existing files as-is, any other non-`/api` path as `index.html` for Vue Router's history
mode. Unknown `/api/*` paths stay JSON 404s. Read by `create_app()` in `tracker/app.py`
(see `tracker/spa.py`); `STATIC_DIR` is read directly from the environment, not through
`Settings`, so `python -m tracker.openapi` still runs without a database URL.

## Run

```sh
DATABASE_URL=postgresql+psycopg://... uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg://... uv run uvicorn tracker.app:app --reload
curl http://127.0.0.1:8000/api/health   # 200 {"status":"ok","database":"ok"}, 503 if the DB is down
```

## Checks

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

`pytest` needs a running Docker daemon: the test session starts a throwaway
Postgres container with testcontainers.

## OpenAPI schema

`uv run python -m tracker.openapi OUTPUT.json` writes the API's OpenAPI schema without
starting a server or touching the database. The frontend's `npm run gen:api` uses it to
regenerate its TypeScript client; run that after changing routes or response models.

## Migrations

Alembic reads `DATABASE_URL` from settings in `migrations/env.py`;
`target_metadata` is `tracker.db.Base.metadata`. Make sure model modules are
imported in `migrations/env.py` so autogenerate sees them, then:

```sh
DATABASE_URL=postgresql+psycopg://... uv run alembic revision --autogenerate -m "describe change"
```

## Test fixtures (`tests/conftest.py`)

- `database_url` (session): a Postgres container migrated to `head`.
- `engine` (session): SQLAlchemy engine for that database.
- `db_session`: a `Session` inside a transaction rolled back after each test.
  `commit()` is safe; commits become savepoints.
- `client`: a FastAPI `TestClient` whose `get_session` dependency yields
  `db_session`, so the test and the app share the same data.
