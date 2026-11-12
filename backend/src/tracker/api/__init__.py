from fastapi import APIRouter

from tracker.api import applications, health

router = APIRouter(prefix="/api")
router.include_router(health.router)
router.include_router(applications.router)
