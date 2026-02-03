from typing import Any

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from api.v1.routers import router

from core.config import settings

# Create FastAPI application
app = FastAPI(
    title= settings.APP_NAME,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins= settings.CORS_ALLOW_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
)

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
