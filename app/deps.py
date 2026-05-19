from collections.abc import AsyncIterator

from arq.connections import ArqRedis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import session_scope
from app.services.job_service import JobService


async def get_db() -> AsyncIterator[AsyncSession]:
    async with session_scope() as session:
        yield session


def get_arq(request: Request) -> ArqRedis:
    pool: ArqRedis | None = getattr(request.app.state, "arq", None)
    if pool is None:
        raise RuntimeError("arq pool not initialised on app.state — check lifespan")
    return pool


async def get_job_service(
    session: AsyncSession = Depends(get_db),
    arq: ArqRedis = Depends(get_arq),
) -> JobService:
    return JobService(session=session, arq=arq)
