# job-application-tracker

A single-user web app for tracking job Applications and the Organizations behind them
(FastAPI + Vue + Postgres, run with Docker Compose). Domain terms are defined in
[`GLOSSARY.md`](GLOSSARY.md); design decisions live in [`docs/adr/`](docs/adr/).

There is no login (ADR 0001): the app is reachable only on `127.0.0.1` or, through
`tailscale serve`, on your private tailnet. Never expose it publicly.

## Run it

```sh
cp .env.example .env      # then set a real POSTGRES_PASSWORD
docker compose up -d --build
open http://127.0.0.1:8000
```

`compose.yaml` runs two services:

- `db`: Postgres (`postgres:17.7-alpine`), data in the named volume `pgdata`, with a
  healthcheck. It publishes **no** host port; only `app` can reach it.
- `app`: one image (`Dockerfile`, multi-stage) that builds the Vue SPA with Node and runs
  the FastAPI backend with `uv`. It waits for `db` to be healthy, runs
  `alembic upgrade head`, then serves the SPA and `/api` from one origin on
  `127.0.0.1:8000`.

To reach it from your tailnet: `tailscale serve --bg 8000`.

Stop with `docker compose down` (add `-v` only if you want to delete the database).

## Develop

Run Postgres in Compose, the backend on the host with reload, and the Vite dev server:

```sh
cp .env.example .env
# 1. Postgres, published on 127.0.0.1:5432 by the dev override
docker compose -f compose.yaml -f compose.dev.yaml up -d db

# 2. Backend with reload on :8000 (credentials from .env)
cd backend
export DATABASE_URL=postgresql+psycopg://tracker:change-me@127.0.0.1:5432/tracker
uv sync
uv run alembic upgrade head
uv run uvicorn tracker.app:app --reload

# 3. Frontend on http://localhost:5173 (proxies /api to :8000)
cd frontend
npm install
npm run dev
```

In development the backend serves only `/api`. It serves the built SPA only when
`STATIC_DIR` points at a build (`frontend/dist`), as the Docker image does.

See [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md)
for checks, migrations and the generated API client.
