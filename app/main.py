from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from arq import create_pool
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.videos import router as videos_router
from app.logging import configure_logging, get_logger
from app.workers.arq_settings import ORCHESTRATOR_QUEUE, redis_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log = get_logger("app")
    log.info("app.start")
    app.state.arq = await create_pool(redis_settings(), default_queue_name=ORCHESTRATOR_QUEUE)
    try:
        yield
    finally:
        await app.state.arq.aclose()
        log.info("app.stop")


def create_app() -> FastAPI:
    app = FastAPI(title="algo-reel", version="0.1.0", lifespan=_lifespan)
    app.include_router(health_router)
    app.include_router(videos_router)
    return app


app = create_app()
