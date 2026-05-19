from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import JobStatus, Renderer
from app.repositories.job_repo import JobRepo


class TestJobRepo:
    async def test_create_inserts_row_with_queued_status(self, clean_db: AsyncSession) -> None:
        repo = JobRepo(clean_db)
        job = await repo.create(
            user_prompt="hello", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
        )

        assert job.id is not None
        assert job.status == JobStatus.QUEUED.value
        assert job.user_prompt == "hello"
        assert job.duration_target_seconds == 60
        assert job.progress == {}

    async def test_get_returns_job_with_scenes_eager_loaded(self, clean_db: AsyncSession) -> None:
        repo = JobRepo(clean_db)
        created = await repo.create(
            user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=30
        )

        fetched = await repo.get(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.scenes == []

    async def test_get_returns_none_when_missing(self, clean_db: AsyncSession) -> None:
        repo = JobRepo(clean_db)
        assert await repo.get(9999) is None

    async def test_update_status_persists(self, clean_db: AsyncSession) -> None:
        repo = JobRepo(clean_db)
        job = await repo.create(
            user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
        )

        await repo.update_status(job.id, JobStatus.SCRIPTING)
        refetched = await repo.get(job.id)

        assert refetched is not None
        assert refetched.status == JobStatus.SCRIPTING.value

    async def test_set_arq_id(self, clean_db: AsyncSession) -> None:
        repo = JobRepo(clean_db)
        job = await repo.create(
            user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
        )

        await repo.set_arq_id(job.id, "arq-abc")
        refetched = await repo.get(job.id)

        assert refetched is not None
        assert refetched.arq_job_id == "arq-abc"

    async def test_set_progress(self, clean_db: AsyncSession) -> None:
        repo = JobRepo(clean_db)
        job = await repo.create(
            user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
        )

        await repo.set_progress(job.id, {"current_scene": 2, "total": 6, "stage": "stub_render"})
        refetched = await repo.get(job.id)

        assert refetched is not None
        assert refetched.progress == {"current_scene": 2, "total": 6, "stage": "stub_render"}

    async def test_get_status_only(self, clean_db: AsyncSession) -> None:
        repo = JobRepo(clean_db)
        job = await repo.create(
            user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
        )

        status = await repo.get_status(job.id)
        assert status == JobStatus.QUEUED

    async def test_get_status_returns_none_when_missing(self, clean_db: AsyncSession) -> None:
        repo = JobRepo(clean_db)
        assert await repo.get_status(9999) is None
