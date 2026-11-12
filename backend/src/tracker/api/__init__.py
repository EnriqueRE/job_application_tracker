from fastapi import APIRouter

from tracker.api import application_events, applications, health, organizations

router = APIRouter(prefix="/api")
router.include_router(health.router)
router.include_router(organizations.router)
router.include_router(applications.router)
router.include_router(application_events.router)
