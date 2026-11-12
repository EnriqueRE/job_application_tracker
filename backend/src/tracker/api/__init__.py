from fastapi import APIRouter

from tracker.api import health, organizations

router = APIRouter(prefix="/api")
router.include_router(health.router)
router.include_router(organizations.router)
