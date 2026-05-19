from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job
from app.domain.enums import JobStatus
from app.domain.state_machine import TERMINAL_JOB_STATUSES, assert_transition
from app.logging import get_logger
from app.repositories.job_repo import JobRepo
from app.schemas.job import CreateJobRequest

log = get_logger("services.job")


class JobNotFoundError(Exception):
    pass


class JobNotCancellableError(Exception):
    pass


class JobService:
    def __init__(self, *, session: AsyncSession, arq: Any) -> None:
        self._repo = JobRepo(session)
        self._arq = arq

    async def create_job(self, req: CreateJobRequest) -> Job:
        job = await self._repo.create(
            user_prompt=req.prompt,
            renderer=req.renderer,
            voice=req.voice,
            duration_target_seconds=req.duration_target,
        )
        arq_job = await self._arq.enqueue_job("run_video", job.id)
        if arq_job is None:
            raise RuntimeError(f"arq.enqueue_job returned None for job {job.id}")
        await self._repo.set_arq_id(job.id, arq_job.job_id)
        refreshed = await self._repo.get(job.id)
        assert refreshed is not None
        log.info("job.created", job_id=job.id, arq_job_id=arq_job.job_id)
        return refreshed

    async def get_job(self, job_id: int) -> Job:
        job = await self._repo.get(job_id)
        if job is None:
            raise JobNotFoundError(f"job {job_id} not found")
        return job

    async def cancel_job(self, job_id: int) -> Job:
        current = await self._repo.get_status(job_id)
        if current is None:
            raise JobNotFoundError(f"job {job_id} not found")
        if current in TERMINAL_JOB_STATUSES:
            raise JobNotCancellableError(f"job {job_id} is in terminal state {current.value}")
        assert_transition(current, JobStatus.CANCELLED)
        await self._repo.update_status(job_id, JobStatus.CANCELLED)
        log.info("job.cancelled", job_id=job_id, from_status=current.value)
        refreshed = await self._repo.get(job_id)
        assert refreshed is not None
        return refreshed
