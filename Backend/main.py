from fastapi import APIRouter, FastAPI

from infrastructure.db.session import init_db
from interfaces.api.middleware.exception import register_exception_handlers
from interfaces.api.v1.alert import router as alert_router
from interfaces.api.v1.user import router as user_router
from interfaces.api.v1.vehicle import router as vehicle_router
from interfaces.api.v1.websocket import router as websocket_router
from shared.config import settings


app = FastAPI(title=settings.APP_NAME)
register_exception_handlers(app)

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(user_router)
api_v1_router.include_router(alert_router)
api_v1_router.include_router(vehicle_router)
api_v1_router.include_router(websocket_router)
app.include_router(api_v1_router)


@app.on_event("startup")
def on_startup() -> None:
    # Keep startup simple for local development.
    init_db()


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}
