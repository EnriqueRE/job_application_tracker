from fastapi import FastAPI

from tracker.api import router as api_router
from tracker.api.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Job Application Tracker")
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
