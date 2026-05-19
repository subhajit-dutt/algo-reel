from decimal import Decimal
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job
from app.domain.enums import JobStatus, Renderer


class JobRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_prompt: str,
        renderer: Renderer,
        voice: str,
        duration_target_seconds: int,
    ) -> Job:
        job = Job(
            user_prompt=user_prompt,
            renderer=renderer.value,
            voice=voice,
            duration_target_seconds=duration_target_seconds,
            status=JobStatus.QUEUED.value,
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: int) -> Job | None:
        result = await self._session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def get_status(self, job_id: int) -> JobStatus | None:
        result = await self._session.execute(select(Job.status).where(Job.id == job_id))
        value = result.scalar_one_or_none()
        if value is None:
            return None
        return JobStatus(value)

    async def update_status(
        self,
        job_id: int,
        status: JobStatus,
        *,
        expected_from: JobStatus | None = None,
    ) -> bool:
        stmt = update(Job).where(Job.id == job_id).values(status=status.value)
        if expected_from is not None:
            stmt = stmt.where(Job.status == expected_from.value)
        result = await self._session.execute(stmt)
        rowcount: int = result.rowcount  # type: ignore[attr-defined]
        return rowcount == 1

    async def set_arq_id(self, job_id: int, arq_job_id: str) -> None:
        await self._session.execute(
            update(Job).where(Job.id == job_id).values(arq_job_id=arq_job_id)
        )

    async def set_progress(self, job_id: int, progress: dict[str, Any]) -> None:
        await self._session.execute(update(Job).where(Job.id == job_id).values(progress=progress))

    async def set_error(self, job_id: int, error: dict[str, Any]) -> None:
        await self._session.execute(update(Job).where(Job.id == job_id).values(error=error))

    async def set_script(self, job_id: int, script: dict[str, Any]) -> None:
        await self._session.execute(
            update(Job).where(Job.id == job_id).values(script=script)
        )

    async def add_cost(self, job_id: int, delta: Decimal) -> None:
        await self._session.execute(
            update(Job).where(Job.id == job_id).values(cost_usd=Job.cost_usd + delta)
        )
