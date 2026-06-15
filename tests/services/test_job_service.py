import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import JobStatus, Renderer, SceneStatus
from app.domain.script import Scene as ScriptScene
from app.domain.script import VideoScript
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo
from app.schemas.job import CreateJobRequest
from app.services.job_service import (
    JobNotCancellableError,
    JobNotFoundError,
    JobNotResumableError,
    JobService,
    OrchestratorPoolDownError,
)


class _FakeArqPool:
    def __init__(self, *, alive: bool = True) -> None:
        self.enqueued: list[tuple[str, tuple, dict]] = []
        self._alive = alive

    async def exists(self, key: str) -> int:
        return 1 if self._alive else 0

    async def enqueue_job(self, name: str, *args, **kwargs) -> "_FakeArqJob":
        self.enqueued.append((name, args, kwargs))
        return _FakeArqJob(job_id=f"arq-{len(self.enqueued)}")


class _FakeArqJob:
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id


class _FakeRedis:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish(self, channel: str, data: str) -> int:
        self.published.append((channel, data))
        return 1


class TestJobServiceCreate:
    async def test_create_inserts_job_and_enqueues(self, clean_db: AsyncSession) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq, redis=_FakeRedis())
        req = CreateJobRequest(
            prompt="explain merge sort", renderer=Renderer.MANIM, duration_target=60, voice="alloy"
        )

        job = await service.create_job(req)

        assert job.id is not None
        assert job.status == JobStatus.QUEUED.value
        assert job.arq_job_id == "arq-1"
        assert arq.enqueued == [("run_video", (job.id,), {})]

    async def test_create_rejects_when_orchestrator_pool_down(self, clean_db: AsyncSession) -> None:
        """No live orchestrator worker (health key absent) must reject job creation —
        an accepted job would sit in `queued` forever with nothing consuming the queue."""
        arq = _FakeArqPool(alive=False)
        service = JobService(session=clean_db, arq=arq, redis=_FakeRedis())
        req = CreateJobRequest(
            prompt="x", renderer=Renderer.MANIM, duration_target=60, voice="alloy"
        )

        with pytest.raises(OrchestratorPoolDownError, match="orchestrator worker"):
            await service.create_job(req)

        # Nothing enqueued and no orphan row left behind.
        assert arq.enqueued == []
        assert await JobRepo(clean_db).get(1) is None


class TestJobServiceCancel:
    async def test_cancel_in_flight_transitions_to_cancelled(self, clean_db: AsyncSession) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq, redis=_FakeRedis())
        req = CreateJobRequest(
            prompt="x", renderer=Renderer.MANIM, duration_target=60, voice="alloy"
        )
        job = await service.create_job(req)

        cancelled = await service.cancel_job(job.id)

        assert cancelled.status == JobStatus.CANCELLED.value

    async def test_cancel_missing_raises_not_found(self, clean_db: AsyncSession) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq, redis=_FakeRedis())
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
        service = JobService(session=clean_db, arq=arq, redis=_FakeRedis())
        req = CreateJobRequest(
            prompt="x", renderer=Renderer.MANIM, duration_target=60, voice="alloy"
        )
        job = await service.create_job(req)
        await JobRepo(clean_db).update_status(job.id, terminal)

        with pytest.raises(JobNotCancellableError):
            await service.cancel_job(job.id)

    async def test_cancel_does_not_clobber_terminal_status(self, clean_db: AsyncSession) -> None:
        """Conditional UPDATE prevents cancel from racing past a terminal transition."""
        from sqlalchemy import text

        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq, redis=_FakeRedis())
        req = CreateJobRequest(
            prompt="x", renderer=Renderer.MANIM, duration_target=60, voice="alloy"
        )
        job = await service.create_job(req)
        # Simulate the worker reaching DONE concurrently — bypass state machine.
        await clean_db.execute(text("UPDATE jobs SET status='done' WHERE id=:i"), {"i": job.id})
        await clean_db.commit()

        with pytest.raises(JobNotCancellableError):
            await service.cancel_job(job.id)

        status = await JobRepo(clean_db).get_status(job.id)
        assert status == JobStatus.DONE  # unchanged


class TestJobServiceResume:
    async def test_resume_resets_failed_scenes_and_transitions_to_rendering(
        self, clean_db: AsyncSession
    ) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq, redis=_FakeRedis())
        req = CreateJobRequest(
            prompt="explain merge sort", renderer=Renderer.MANIM, duration_target=60, voice="alloy"
        )
        job = await service.create_job(req)

        script = VideoScript(
            title="Merge sort",
            renderer=Renderer.MANIM,
            voice="alloy",
            total_duration=10.0,
            scenes=[
                ScriptScene(index=0, narration="a", visual_prompt="p0", duration_seconds=5.0),
                ScriptScene(index=1, narration="b", visual_prompt="p1", duration_seconds=5.0),
            ],
        )
        scene_repo = SceneRepo(clean_db)
        scenes = await scene_repo.bulk_insert_from_script(job.id, script)
        await scene_repo.update_status(scenes[0].id, SceneStatus.DONE)
        await scene_repo.update_status(scenes[1].id, SceneStatus.FAILED)
        await JobRepo(clean_db).update_status(job.id, JobStatus.PARTIALLY_FAILED)
        await clean_db.commit()

        resumed = await service.resume_job(job.id)

        assert resumed.status == JobStatus.RENDERING.value
        assert ("run_video", (job.id,), {}) in arq.enqueued

        clean_db.expunge_all()
        refetched = await SceneRepo(clean_db).list_by_job(job.id)
        assert refetched[0].status == SceneStatus.DONE.value
        assert refetched[1].status == SceneStatus.PENDING.value

    async def test_resume_rejects_non_partial_job(self, clean_db: AsyncSession) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq, redis=_FakeRedis())
        req = CreateJobRequest(
            prompt="x", renderer=Renderer.MANIM, duration_target=60, voice="alloy"
        )
        job = await service.create_job(req)  # default QUEUED state

        with pytest.raises(JobNotResumableError):
            await service.resume_job(job.id)


class TestJobServiceGet:
    async def test_get_returns_job(self, clean_db: AsyncSession) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq, redis=_FakeRedis())
        req = CreateJobRequest(
            prompt="x", renderer=Renderer.MANIM, duration_target=60, voice="alloy"
        )
        created = await service.create_job(req)

        fetched = await service.get_job(created.id)

        assert fetched.id == created.id

    async def test_get_missing_raises_not_found(self, clean_db: AsyncSession) -> None:
        arq = _FakeArqPool()
        service = JobService(session=clean_db, arq=arq, redis=_FakeRedis())
        with pytest.raises(JobNotFoundError):
            await service.get_job(9999)
