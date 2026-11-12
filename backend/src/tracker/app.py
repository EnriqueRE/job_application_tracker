import os
from pathlib import Path

from fastapi import FastAPI

from tracker.api import router as api_router
from tracker.spa import mount_spa


def create_app(static_dir: Path | None = None) -> FastAPI:
    """Build the app.

    ``static_dir`` is the built SPA (Vite ``dist/``) to serve next to ``/api``; it
    defaults to the ``STATIC_DIR`` environment variable. Without either, only the
    API is served (the dev setup, where Vite serves the SPA).
    """
    app = FastAPI(title="Job Application Tracker")
    app.include_router(api_router)
    if static_dir is None and (env_static_dir := os.environ.get("STATIC_DIR")):
        static_dir = Path(env_static_dir)
    if static_dir is not None:
        mount_spa(app, static_dir)
    return app


app = create_app()
