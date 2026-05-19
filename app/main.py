from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.videos import router as videos_router
from app.logging import configure_logging, get_logger


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    get_logger("app").info("app.start")
    yield
    get_logger("app").info("app.stop")


def create_app() -> FastAPI:
    app = FastAPI(title="algo-reel", version="0.1.0", lifespan=_lifespan)
    app.include_router(health_router)
    app.include_router(videos_router)
    return app


app = create_app()
