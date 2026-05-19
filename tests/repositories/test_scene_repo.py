from decimal import Decimal

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Renderer, SceneStatus
from app.domain.script import Scene as DomainScene
from app.domain.script import VideoScript
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


def _script() -> VideoScript:
    return VideoScript(
        title="t",
        renderer=Renderer.MANIM,
        voice="alloy",
        total_duration=60.0,
        scenes=[
            DomainScene(index=0, narration="A", visual_prompt="vA", duration_seconds=20.0),
            DomainScene(index=1, narration="B", visual_prompt="vB", duration_seconds=20.0),
            DomainScene(index=2, narration="C", visual_prompt="vC", duration_seconds=20.0),
        ],
    )


class TestBulkInsertFromScript:
    async def test_inserts_in_order(self, clean_db) -> None:  # type: ignore[no-untyped-def]
        job = await JobRepo(clean_db).create(
            user_prompt="p",
            renderer=Renderer.MANIM,
            voice="alloy",
            duration_target_seconds=60,
        )
        await clean_db.commit()

        repo = SceneRepo(clean_db)
        await repo.bulk_insert_from_script(job.id, _script())
        await clean_db.commit()

        scenes = await repo.list_by_job(job.id)
        assert [s.index for s in scenes] == [0, 1, 2]
        assert [s.narration for s in scenes] == ["A", "B", "C"]
        assert [s.visual_prompt for s in scenes] == ["vA", "vB", "vC"]
        assert all(s.status == SceneStatus.PENDING.value for s in scenes)
        assert scenes[0].duration_seconds == Decimal("20.00")
