from collections.abc import AsyncIterator

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_session_factory
from app.services.job_service import JobService
from app.workers.arq_settings import ORCHESTRATOR_QUEUE


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_arq(settings: Settings = Depends(get_settings)) -> ArqRedis:
    return await create_pool(
        RedisSettings.from_dsn(settings.redis_url),
        default_queue_name=ORCHESTRATOR_QUEUE,
    )


async def get_job_service(
    session: AsyncSession = Depends(get_db),
    arq: ArqRedis = Depends(get_arq),
) -> JobService:
    return JobService(session=session, arq=arq)
