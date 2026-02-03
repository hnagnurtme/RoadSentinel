from fastapi import FastAPI
from rest_framework.request import Request
from starlette.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from exceptions.base import AppException


def register_exception_handlers(app : FastAPI) -> None :

    @app.exception_handler(AppException)
    async  def app_exception_handler(
            request : Request ,
            exceptions : AppException
    ) :
        return JSONResponse(
            status_code = exceptions.status_code,
            content = {
               "success" : False,
               "message" : exceptions.message,
               "error_code" : exceptions.error_code,
               "detail" : exceptions.detail,
               "path" : request.url.path
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
            request: Request,
            exc: RequestValidationError,
    ):
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Validation error",
                "error_code": "VALIDATION_ERROR",
                "detail": exc.errors(),
                "path": request.url.path,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
            request: Request,
            exc: StarletteHTTPException,
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "error_code": "HTTP_EXCEPTION",
                "path": request.url.path,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
            request: Request,
            exc: Exception,
    ):
        # TODO: log exception here (Sentry, logging, etc.)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "path": request.url.path,
            },
        )