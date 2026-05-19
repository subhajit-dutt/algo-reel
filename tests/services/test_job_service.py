import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import JobStatus, Renderer
from app.repositories.job_repo import JobRepo
from app.schemas.job import CreateJobRequest
from app.services.job_service import JobNotCancellableError, JobNotFoundError, JobService


class _FakeArqPool:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, tuple, dict]] = []

    async def enqueue_job(self, name: str, *args, **kwargs) -> "_FakeArqJob":
        self.enqueued.append((name, args, kwargs))
        return _FakeArqJob(job_id=f"arq-{len(self.enqueued)}")


class _FakeArqJob:
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id


class TestJobServiceCreate:
    async def test_create_inserts_job_and_enqueues(
        self, clean_db: AsyncSession
    ) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq)
        req = CreateJobRequest(
            prompt="explain merge sort", renderer=Renderer.MANIM, duration_target=60, voice="alloy"
        )

        job = await service.create_job(req)

        assert job.id is not None
        assert job.status == JobStatus.QUEUED.value
        assert job.arq_job_id == "arq-1"
        assert arq.enqueued == [("run_video", (job.id,), {})]


class TestJobServiceCancel:
    async def test_cancel_in_flight_transitions_to_cancelled(
        self, clean_db: AsyncSession
    ) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq)
        req = CreateJobRequest(
            prompt="x", renderer=Renderer.MANIM, duration_target=60, voice="alloy"
        )
        job = await service.create_job(req)

        cancelled = await service.cancel_job(job.id)

        assert cancelled.status == JobStatus.CANCELLED.value

    async def test_cancel_missing_raises_not_found(
        self, clean_db: AsyncSession
    ) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq)
        with pytest.raises(JobNotFoundError):
            await service.cancel_job(9999)

    @pytest.mark.parametrize(
        "terminal",
        [JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.PARTIALLY_FAILED],
    )
    async def test_cancel_in_terminal_state_raises(
        self, clean_db: AsyncSession, terminal: JobStatus
    ) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq)
        req = CreateJobRequest(
            prompt="x", renderer=Renderer.MANIM, duration_target=60, voice="alloy"
        )
        job = await service.create_job(req)
        await JobRepo(clean_db).update_status(job.id, terminal)

        with pytest.raises(JobNotCancellableError):
            await service.cancel_job(job.id)


class TestJobServiceGet:
    async def test_get_returns_job(self, clean_db: AsyncSession) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq)
        req = CreateJobRequest(
            prompt="x", renderer=Renderer.MANIM, duration_target=60, voice="alloy"
        )
        created = await service.create_job(req)

        fetched = await service.get_job(created.id)

        assert fetched.id == created.id

    async def test_get_missing_raises_not_found(self, clean_db: AsyncSession) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq)
        with pytest.raises(JobNotFoundError):
            await service.get_job(9999)
