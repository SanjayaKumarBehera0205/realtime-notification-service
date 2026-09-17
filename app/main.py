from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, notifications, websocket
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.realtime.broker import broker
from app.realtime.manager import manager


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    await broker.start()
    yield
    await broker.stop()


app = FastAPI(
    title=settings.app_name,
    description="JWT-protected REST and WebSocket notification service with Redis Pub/Sub.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(notifications.router, prefix=settings.api_prefix)
app.include_router(websocket.router)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str | int]:
    return {"status": "healthy", "active_websockets": manager.active_connections}
