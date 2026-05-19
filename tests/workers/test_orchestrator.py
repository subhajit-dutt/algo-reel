import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import JobStatus, Renderer, SceneStatus
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo
from app.workers.orchestrator import STUB_SCENE_COUNT, run_video


@pytest_asyncio.fixture
async def job_id(clean_db: AsyncSession) -> int:
    repo = JobRepo(clean_db)
    job = await repo.create(
        user_prompt="hello", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
    )
    await clean_db.commit()
    return job.id


class TestRunVideo:
    async def test_walks_job_to_done(self, clean_db: AsyncSession, job_id: int) -> None:
        await run_video({"_test_no_sleep": True}, job_id)

        job = await JobRepo(clean_db).get(job_id)
        assert job is not None
        assert job.status == JobStatus.DONE.value
        assert job.progress == {
            "current_scene": STUB_SCENE_COUNT,
            "total": STUB_SCENE_COUNT,
            "stage": "stub_render",
        }

    async def test_creates_stub_scenes_and_marks_them_done(
        self, clean_db: AsyncSession, job_id: int
    ) -> None:
        await run_video({"_test_no_sleep": True}, job_id)

        scenes = await SceneRepo(clean_db).list_by_job(job_id)
        assert len(scenes) == STUB_SCENE_COUNT
        assert all(s.status == SceneStatus.DONE.value for s in scenes)

    async def test_aborts_when_already_cancelled(self, clean_db: AsyncSession, job_id: int) -> None:
        await JobRepo(clean_db).update_status(job_id, JobStatus.CANCELLED)
        await clean_db.commit()

        await run_video({"_test_no_sleep": True}, job_id)

        job = await JobRepo(clean_db).get(job_id)
        assert job is not None
        assert job.status == JobStatus.CANCELLED.value
        scenes = await SceneRepo(clean_db).list_by_job(job_id)
        assert scenes == []

    async def test_noop_when_job_missing(self, clean_db: AsyncSession) -> None:
        await run_video({"_test_no_sleep": True}, 9999)

    async def test_resume_skips_when_already_done(
        self, clean_db: AsyncSession, job_id: int
    ) -> None:
        # Bypass state machine to plant a terminal status directly for the test.
        from sqlalchemy import text

        await clean_db.execute(text("UPDATE jobs SET status='done' WHERE id=:i"), {"i": job_id})
        await clean_db.commit()

        await run_video({"_test_no_sleep": True}, job_id)
        await run_video({"_test_no_sleep": True}, job_id)

        job = await JobRepo(clean_db).get(job_id)
        assert job is not None
        assert job.status == JobStatus.DONE.value
