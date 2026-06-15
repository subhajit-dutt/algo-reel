from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job
from app.domain.enums import JobStatus, SceneStatus
from app.domain.state_machine import TERMINAL_JOB_STATUSES, assert_transition
from app.logging import get_logger
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo
from app.schemas.event import ProgressEvent
from app.schemas.job import CreateJobRequest
from app.services.progress_publisher import ProgressPublisher
from app.workers.queues import (
    ORCHESTRATOR_POOL_HEALTH_KEY,
    ORCHESTRATOR_QUEUE,
    RENDER_POOL_HEALTH_KEY,
)

log = get_logger("services.job")

_ORCHESTRATOR_POOL_DOWN_MSG = (
    f"no live orchestrator worker on the '{ORCHESTRATOR_QUEUE}' queue — "
    "start one with `make worker`"
)
_RENDER_POOL_DOWN_MSG = (
    "no live render worker on the 'render_pool' queue — start one with `make render-worker`"
)


class JobNotFoundError(Exception):
    pass


class JobNotCancellableError(Exception):
    pass


class JobNotResumableError(Exception):
    pass


class OrchestratorPoolDownError(Exception):
    pass


class RenderPoolDownError(Exception):
    pass


class JobService:
    def __init__(self, *, session: AsyncSession, arq: Any, redis: Any) -> None:
        self._session = session
        self._repo = JobRepo(session)
        self._arq = arq
        self._publisher = ProgressPublisher(redis)

    async def create_job(self, req: CreateJobRequest) -> Job:
        # Guard before the insert: with no consumer on the orchestrator queue the
        # job would sit in `queued` forever, so reject rather than persist a row
        # nothing will ever pick up.
        if not await self._arq.exists(ORCHESTRATOR_POOL_HEALTH_KEY):
            raise OrchestratorPoolDownError(_ORCHESTRATOR_POOL_DOWN_MSG)
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
        await self._session.refresh(job)
        log.info("job.created", job_id=job.id, arq_job_id=arq_job.job_id)
        return job

    async def resume_job(self, job_id: int) -> Job:
        job = await self._repo.get(job_id)
        if job is None:
            raise JobNotFoundError(f"job {job_id} not found")
        if JobStatus(job.status) is not JobStatus.PARTIALLY_FAILED:
            raise JobNotResumableError(
                f"job {job_id} is {job.status}, only partially_failed jobs can be resumed"
            )
        if not await self._arq.exists(ORCHESTRATOR_POOL_HEALTH_KEY):
            raise OrchestratorPoolDownError(_ORCHESTRATOR_POOL_DOWN_MSG)
        if not await self._arq.exists(RENDER_POOL_HEALTH_KEY):
            raise RenderPoolDownError(_RENDER_POOL_DOWN_MSG)

        scene_repo = SceneRepo(self._session)
        for scene in await scene_repo.list_by_job(job_id):
            if scene.status == SceneStatus.FAILED.value:
                await scene_repo.update_status(scene.id, SceneStatus.PENDING)
        assert_transition(JobStatus.PARTIALLY_FAILED, JobStatus.RENDERING)
        updated = await self._repo.update_status(
            job_id, JobStatus.RENDERING, expected_from=JobStatus.PARTIALLY_FAILED
        )
        if not updated:
            raise JobNotResumableError(f"job {job_id} could not transition to rendering")
        await self._session.commit()
        arq_job = await self._arq.enqueue_job("run_video", job_id)
        if arq_job is None:
            raise RuntimeError(f"arq.enqueue_job returned None for resume {job_id}")
        await self._repo.set_arq_id(job_id, arq_job.job_id)
        log.info("job.resumed", job_id=job_id, arq_job_id=arq_job.job_id)
        refreshed = await self._repo.get(job_id)
        assert refreshed is not None
        return refreshed

    async def get_job(self, job_id: int) -> Job:
        job = await self._repo.get(job_id)
        if job is None:
            raise JobNotFoundError(f"job {job_id} not found")
        return job

    async def cancel_job(self, job_id: int) -> Job:
        non_terminal = frozenset(JobStatus) - TERMINAL_JOB_STATUSES
        updated = await self._repo.update_status(
            job_id, JobStatus.CANCELLED, expected_from=non_terminal
        )
        if not updated:
            current = await self._repo.get_status(job_id)
            if current is None:
                raise JobNotFoundError(f"job {job_id} not found")
            raise JobNotCancellableError(f"job {job_id} is in terminal state {current.value}")
        # Commit the cancel before publishing so an SSE consumer's subsequent
        # snapshot read (if it reconnects) is consistent with the event payload.
        await self._session.commit()
        log.info("job.cancelled", job_id=job_id)
        await self._publisher.publish(
            ProgressEvent(
                event="cancelled",
                job_id=job_id,
                status=JobStatus.CANCELLED,
                progress={},
            )
        )
        refreshed = await self._repo.get(job_id)
        assert refreshed is not None
        return refreshed
