from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from interfaces.api.middleware.exception import register_exception_handlers
from interfaces.api.v1.alert import router as alert_router
from interfaces.api.v1.user import router as user_router
from interfaces.api.v1.vehicle import router as vehicle_router
from interfaces.api.v1.websocket import router as websocket_router
from shared.config import settings


app = FastAPI(title=settings.APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)
register_exception_handlers(app)

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(user_router)
api_v1_router.include_router(alert_router)
api_v1_router.include_router(vehicle_router)
api_v1_router.include_router(websocket_router)
app.include_router(api_v1_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}
