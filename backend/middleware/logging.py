import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(
            self,
            request: Request,
            call_next: Callable,
    ) -> Response:

        request_id = request.headers.get("X-Request-ID", "unknown")

        start_time = time.perf_counter()

        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=str(request.query_params) if request.query_params else None,
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            # Log exception
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                error=str(exc),
            )
            raise

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log response
        log_func = logger.info if response.status_code < 400 else logger.warning
        log_func(
            "Request completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response
