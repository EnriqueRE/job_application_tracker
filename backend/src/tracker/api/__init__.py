from fastapi import APIRouter

from tracker.api import application_events, health, organizations

router = APIRouter(prefix="/api")
router.include_router(health.router)
router.include_router(application_events.router)
router.include_router(organizations.router)
