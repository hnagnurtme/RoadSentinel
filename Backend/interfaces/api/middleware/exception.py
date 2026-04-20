"""
interfaces/api/middleware/exception.py
---------------------------------------
Centralised FastAPI exception handlers.

Registered via ``register_exception_handlers(app)`` in ``main.py``.

Handles:
- ``AppException`` subclasses   — returns structured JSON with the appropriate
  HTTP status code.
- ``RequestValidationError``    — returns 422 with field-level error details.
- Catch-all ``Exception``       — returns 500 and logs the full traceback so
  unexpected errors are never silently swallowed.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from interfaces.api.response import error_response
from shared.exceptions import AppException

logger = logging.getLogger("roadsentinel.exceptions")


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to *app*."""

    @app.exception_handler(AppException)
    async def _app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message=exc.message, code=exc.code),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Surface the first validation error as the message for easy debugging.
        first_error = exc.errors()[0] if exc.errors() else {}
        message = first_error.get("msg", "Request validation failed")
        return JSONResponse(
            status_code=422,
            content={
                **error_response(message=message, code="VALIDATION_ERROR"),
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def _unknown_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content=error_response(message="Internal server error", code="INTERNAL_ERROR"),
        )
