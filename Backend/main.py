"""
main.py
-------
FastAPI application factory.

Startup sequence
----------------
1. ``lifespan`` loads the YOLO model in a thread pool so the event loop is
   not blocked during the potentially-long model initialisation.
2. CORS, static-file serving, and exception handlers are registered.
3. Routers are mounted under ``/api/v1``.
4. The ESP32 camera WebSocket is *also* mounted at the legacy path ``/ws/camera``
   for hardware compatibility (Arduino firmware hardcodes this path).
"""
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
from interfaces.api.v1.user import router as user_router
from interfaces.api.v1.vehicle import router as vehicle_router
from interfaces.api.v1.websocket import camera_websocket, router as websocket_router
from shared.config import settings

logger = logging.getLogger("roadsentinel.main")

# ── Application lifespan ──────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Load the AI model at startup (non-blocking)."""
    print("=== LIFESPAN STARTING - NEW CODE LOADED ===")
    logger.info("Starting up RoadSentinel backend...")
    logger.info("About to load AI model...")
    try:
        await asyncio.to_thread(inference_engine.load)
        logger.info("AI model loading completed.")
        logger.info(f"AI engine ready: {inference_engine.is_ready}")
        print(f"=== AI ENGINE READY: {inference_engine.is_ready} ===")
    except Exception as e:
        logger.error(f"AI model loading failed: {e}")
        print(f"=== AI MODEL LOADING FAILED: {e} ===")
    logger.info("Startup complete.")
    print("=== STARTUP COMPLETE ===")
    yield
    logger.info("Shutting down RoadSentinel backend.")


# ── Application factory ───────────────────────────────────────────────────────


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="RoadSentinel — AI-powered driver monitoring backend.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── Static files (evidence clips) ─────────────────────────────────────
    evidence_dir = Path(__file__).resolve().parent / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/evidence", StaticFiles(directory=str(evidence_dir)), name="evidence")

    # ── Middleware ─────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    register_exception_handlers(app)

    # ── ESP32 legacy route ─────────────────────────────────────────────────
    # The Arduino firmware hardcodes WS_PATH = "/ws/camera" so we expose the
    # handler at that path in addition to the versioned /api/v1/ws/camera.
    app.add_api_websocket_route("/ws/camera", camera_websocket)

    # ── REST + versioned WebSocket ─────────────────────────────────────────
    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(user_router)
    api_v1.include_router(alert_router)
    api_v1.include_router(vehicle_router)
    api_v1.include_router(websocket_router)
    app.include_router(api_v1)

    # ── Health check ───────────────────────────────────────────────────────
    @app.get("/", tags=["health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
