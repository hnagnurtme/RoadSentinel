from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from interfaces.api.response import error_response
from shared.exceptions import AppException


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(_: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message=exc.message, code=exc.code),
        )

    @app.exception_handler(Exception)
    async def unknown_exception_handler(_: Request, __: Exception):
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Internal server error", code="internal_error"
            ),
        )
