"""Map domain errors raised by the services to HTTP responses (body ``{"detail": str}``)."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tracker.services.errors import ConflictError, InvalidValueError, NotFoundError

ERROR_STATUS: dict[type[Exception], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    InvalidValueError: 422,
}


def register_error_handlers(app: FastAPI) -> None:
    for error_class, status_code in ERROR_STATUS.items():
        app.add_exception_handler(error_class, _handler(status_code))


def _handler(status_code: int) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handle(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handle
