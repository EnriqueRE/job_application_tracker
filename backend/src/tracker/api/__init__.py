from fastapi import APIRouter

from tracker.api import health

router = APIRouter(prefix="/api")
router.include_router(health.router)
