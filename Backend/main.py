import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from interfaces.api.middleware.exception import register_exception_handlers
from interfaces.api.v1.alert import router as alert_router
from interfaces.api.v1.user import router as user_router
from interfaces.api.v1.vehicle import router as vehicle_router
from interfaces.api.v1.websocket import router as websocket_router, camera_websocket, _load_model
from shared.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load YOLO model in a thread pool so it doesn't block the event loop
    await asyncio.to_thread(_load_model)
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

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

# ── ESP32 compatibility route: Arduino hardcodes WS_PATH = "/ws/camera" ─────────
# Mount the camera handler directly at /ws/camera (no /api/v1 prefix needed).
app.add_api_websocket_route("/ws/camera", camera_websocket)

# ── REST API + versioned WebSocket for browser clients (Frontend) ──────────────
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(user_router)
api_v1_router.include_router(alert_router)
api_v1_router.include_router(vehicle_router)
api_v1_router.include_router(websocket_router)  # /api/v1/ws/{alerts,camera,frontend}
app.include_router(api_v1_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}
