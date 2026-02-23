from typing import Any

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from api.v1.routers import router

from core.config import settings
from middleware.exception import ExceptionMiddleware
from middleware.request_id import RequestIdMiddleware

# Create FastAPI application
app = FastAPI(
    title= settings.APP_NAME,
)
# ============================================================
# Middleware Stack (order matters - executed in reverse order)
# ============================================================

# 1. CORS - outermost, handles preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 2. Exception Handler - catches all exceptions from inner middleware
app.add_middleware(ExceptionMiddleware)

# 3. RequestID
app.add_middleware(RequestIdMiddleware)


# Routers
app.include_router(router)

@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    """Root endpoint - API information."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
