"""Serve the built single-page app (Vite ``dist/``) next to ``/api``.

Existing files are served as-is; any other non-API path returns ``index.html`` so
Vue Router's history mode can handle deep links. Paths under ``/api`` never fall
back: an unknown API route stays a JSON 404.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def mount_spa(app: FastAPI, static_dir: Path) -> None:
    root = static_dir.resolve()
    index = root / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (root / path).resolve()
        if candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index)
