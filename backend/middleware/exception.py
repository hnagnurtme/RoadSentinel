from typing import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.logging import get_logger
from exceptions import AppException, ErrorCodes, ErrorResponse, Messages


logger = get_logger(__name__)


class ExceptionMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")

        try:
            return await call_next(request)

        except AppException as exc:
            logger.warning(
                "Application exception",
                request_id=request_id,
                error_code=exc.error_code,
                message=exc.message,
                path=str(request.url),
            )
            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponse(
                    message=exc.message,
                    error_code=exc.error_code,
                    details=exc.details,
                ).model_dump(),
            )

        except IntegrityError as exc:
            logger.error(
                "Database integrity error",
                request_id=request_id,
                path=str(request.url),
                error=str(exc.orig) if exc.orig else str(exc),
            )
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=ErrorResponse(
                    message=Messages.CONFLICT,
                    error_code=ErrorCodes.INTEGRITY_ERROR,
                ).model_dump(),
            )

        except SQLAlchemyError:
            logger.exception(
                "Database error",
                request_id=request_id,
                path=str(request.url),
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=ErrorResponse(
                    message=Messages.INTERNAL_ERROR,
                    error_code=ErrorCodes.DATABASE_ERROR,
                ).model_dump(),
            )

        except Exception as exc:
            logger.exception(
                "Unexpected error",
                request_id=request_id,
                error=str(exc),
                error_type=type(exc).__name__,
                path=str(request.url),
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=ErrorResponse(
                    message=Messages.INTERNAL_ERROR,
                    error_code=ErrorCodes.INTERNAL_ERROR,
                ).model_dump(),
            )
