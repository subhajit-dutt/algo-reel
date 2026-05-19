from decimal import Decimal

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Renderer, SceneStatus
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo


@pytest_asyncio.fixture
async def job_id(clean_db: AsyncSession) -> int:
    repo = JobRepo(clean_db)
    job = await repo.create(
        user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
    )
    return job.id


class TestSceneRepo:
    async def test_bulk_insert_stubs_inserts_n_scenes_in_order(
        self, clean_db: AsyncSession, job_id: int
    ) -> None:
        repo = SceneRepo(clean_db)

        scenes = await repo.bulk_insert_stubs(job_id=job_id, n=3)

        assert len(scenes) == 3
        assert [s.index for s in scenes] == [0, 1, 2]
        assert all(s.status == SceneStatus.PENDING.value for s in scenes)
        assert all(s.duration_seconds == Decimal("0.00") for s in scenes)

    async def test_list_by_job_returns_ordered(self, clean_db: AsyncSession, job_id: int) -> None:
        repo = SceneRepo(clean_db)
        await repo.bulk_insert_stubs(job_id=job_id, n=4)

        scenes = await repo.list_by_job(job_id)

        assert [s.index for s in scenes] == [0, 1, 2, 3]

    async def test_update_status_persists(self, clean_db: AsyncSession, job_id: int) -> None:
        repo = SceneRepo(clean_db)
        scenes = await repo.bulk_insert_stubs(job_id=job_id, n=2)

        await repo.update_status(scenes[0].id, SceneStatus.DONE)

        refetched = await repo.list_by_job(job_id)
        assert refetched[0].status == SceneStatus.DONE.value
        assert refetched[1].status == SceneStatus.PENDING.value
