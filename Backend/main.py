"""FastAPI application factory for RoadSentinel."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.ai.engine import inference_engine
from interfaces.api.middleware.exception import register_exception_handlers
from interfaces.api.v1.alert import router as alert_router
from interfaces.api.v1.auth import router as auth_router
from interfaces.api.v1.appeal import router as appeal_router
from interfaces.api.v1.user import router as user_router
from interfaces.api.v1.vehicle import router as vehicle_router
from interfaces.api.v1.websocket import camera_websocket, router as websocket_router
from shared.config import settings

logger = logging.getLogger("roadsentinel.main")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Load the AI model at startup (non-blocking)."""
    logger.info("Starting up RoadSentinel backend...")
    try:
        await asyncio.to_thread(inference_engine.load)
        logger.info("AI model loading completed.")
    except Exception as e:
        logger.error(f"AI model loading failed: {e}")
    logger.info("Startup complete.")
    yield
    logger.info("Shutting down RoadSentinel backend.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="RoadSentinel — AI-powered driver monitoring backend.",
        version="1.0.0",
        lifespan=lifespan,
    )

    evidence_dir = Path(__file__).resolve().parent / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/evidence", StaticFiles(directory=str(evidence_dir)), name="evidence")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    register_exception_handlers(app)

    app.add_api_websocket_route("/ws/camera", camera_websocket)

    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(user_router)
    api_v1.include_router(alert_router)
    api_v1.include_router(vehicle_router)
    api_v1.include_router(websocket_router)
    api_v1.include_router(auth_router)
    api_v1.include_router(appeal_router)
    app.include_router(api_v1)

    @app.get("/", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
