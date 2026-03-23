from fastapi import FastAPI

from infrastructure.db.session import init_db
from interfaces.api.middleware.exception import register_exception_handlers
from interfaces.api.v1.user import router as user_router
from shared.config import settings


app = FastAPI(title=settings.APP_NAME)
register_exception_handlers(app)
app.include_router(user_router)


@app.on_event("startup")
def on_startup() -> None:
    # Keep startup simple for local development.
    init_db()


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}
