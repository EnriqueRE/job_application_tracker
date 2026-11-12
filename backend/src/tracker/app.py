from fastapi import FastAPI

from tracker.api import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="Job Application Tracker")
    app.include_router(api_router)
    return app


app = create_app()
