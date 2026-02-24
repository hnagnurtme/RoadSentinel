from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from constants import Messages
from db.base import AsyncSessionLocal
from schemas import ApiResponse


router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=ApiResponse[dict[str, Any]],
    summary="Health check",
    description="Returns API and database health status.",
)
async def health_check() -> ApiResponse[dict[str, Any]]:
    db_status = "healthy"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    return ApiResponse(
        message=Messages.API_HEALTHY,
        data={"api": "healthy", "database": db_status},
    )
