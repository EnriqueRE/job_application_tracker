from fastapi import APIRouter

from tracker.api import application_events, applications, health

router = APIRouter(prefix="/api")
router.include_router(health.router)
router.include_router(applications.router)
router.include_router(application_events.router)
