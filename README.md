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

`compose.yaml` runs three services:

- `db`: Postgres (`postgres:17.7-alpine`), data in the named volume `pgdata`, with a
  healthcheck. It publishes **no** host port; only `app` and `backup` reach it.
- `app`: one image (`Dockerfile`, multi-stage) that builds the Vue SPA with Node and runs
  the FastAPI backend with `uv`. It waits for `db` to be healthy, runs
  `alembic upgrade head`, then serves the SPA and `/api` from one origin on
  `127.0.0.1:8000`.
- `backup`: nightly `pg_dump` into `./backups` (see [Backups](#backups)).

To reach it from your tailnet: `tailscale serve --bg 8000`.

Stop with `docker compose down` (add `-v` only if you want to delete the database).

## Backups

The `backup` service (same `postgres:17.7-alpine` image, scripts in [`backup/`](backup/))
runs `pg_dump --format=custom` every night and writes
`./backups/tracker-<UTC timestamp>.dump` (the directory is gitignored). After each
successful dump it deletes all but the 14 newest `tracker-*.dump` files; other files in
`./backups` are left alone. A failed dump leaves no file and prunes nothing.

Settings (optional, in `.env`; see `.env.example`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `BACKUP_TIME` | `03:00` | Daily run time, `HH:MM` |
| `BACKUP_TZ` | `UTC` | Timezone for `BACKUP_TIME`, e.g. `Europe/Madrid` |
| `BACKUP_KEEP` | `14` | Number of dumps to keep |
| `BACKUP_UID` / `BACKUP_GID` | `1000` | Owner of the dump files; set to `id -u` / `id -g` |

Check it is running with `docker compose logs backup`.

**Take a backup now:**

```sh
docker compose exec backup /backup/backup.sh
```

**Restore** a dump into a fresh database (this deletes the current data):

```sh
docker compose down -v                 # deletes the pgdata volume; ./backups is kept
docker compose up -d --wait db         # new, empty database
docker compose exec -T db sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --exit-on-error --single-transaction' \
  < backups/tracker-YYYYMMDDTHHMMSSZ.dump
docker compose up -d                   # start app and backup again
```

Restore before starting `app`: on start it runs `alembic upgrade head`, which would create
empty tables that clash with the restore. The dump includes the `alembic_version` table,
so `app` then applies only migrations newer than the backup.

The retention logic is tested by `backend/tests/test_backup_script.py` (runs the script
with a stub `pg_dump`); `backend/tests/test_backup_restore.py` runs the script against a
real Postgres and restores the dump into a fresh one with the `pg_restore` command above.

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
