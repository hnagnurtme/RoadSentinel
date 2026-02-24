from fastapi import APIRouter

from api.v1.endpoints import auth, health, users

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(health.router)