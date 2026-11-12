"""Map domain errors raised by the services to HTTP responses with a ``{"detail": str}`` body."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tracker.services.errors import ConflictError, InvalidValueError, NotFoundError

STATUS_CODES: dict[type[Exception], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    InvalidValueError: 422,
}


def register_error_handlers(app: FastAPI) -> None:
    for error_type, status_code in STATUS_CODES.items():

        def handler(
            _request: Request, exc: Exception, status_code: int = status_code
        ) -> JSONResponse:
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})

        app.add_exception_handler(error_type, handler)
