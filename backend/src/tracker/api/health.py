from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from tracker.db import get_session

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: Literal["ok", "error"]
    database: Literal["ok", "unreachable"]


@router.get(
    "/health",
    response_model=HealthStatus,
    responses={503: {"model": HealthStatus, "description": "The database is unreachable"}},
)
def health(session: Annotated[Session, Depends(get_session)]) -> JSONResponse:
    """Report whether the app is up and can reach its database."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "error", "database": "unreachable"})
    return JSONResponse(content={"status": "ok", "database": "ok"})
