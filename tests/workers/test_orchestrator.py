from collections.abc import AsyncIterator
from decimal import Decimal

import pytest_asyncio
from pydantic_ai import models
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import JobStatus, Renderer, SceneStatus
from app.domain.script import Scene as DomainScene
from app.domain.script import VideoScript
from app.llm.script_agent import script_agent
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo
from app.workers.orchestrator import run_video

models.ALLOW_MODEL_REQUESTS = False


def _canned(n: int = 3, total: float = 60.0) -> VideoScript:
    per = total / n
    return VideoScript(
        title="t",
        renderer=Renderer.MANIM,
        voice="alloy",
        total_duration=total,
        scenes=[
            DomainScene(
                index=i, narration=f"n{i}", visual_prompt=f"v{i}", duration_seconds=per
            )
            for i in range(n)
        ],
    )


@pytest_asyncio.fixture
async def job_id(clean_db: AsyncSession) -> int:
    repo = JobRepo(clean_db)
    job = await repo.create(
        user_prompt="hello",
        renderer=Renderer.MANIM,
        voice="alloy",
        duration_target_seconds=60,
    )
    await clean_db.commit()
    return job.id


@pytest_asyncio.fixture
async def overridden_agent() -> AsyncIterator[None]:
    with script_agent.override(model=TestModel(custom_output_args=_canned().model_dump())):
        yield


class TestRunVideo:
    async def test_walks_job_to_done(
        self, clean_db: AsyncSession, job_id: int, overridden_agent: None
    ) -> None:
        await run_video({"_test_no_sleep": True}, job_id)

        job = await JobRepo(clean_db).get(job_id)
        assert job is not None
        assert job.status == JobStatus.DONE.value
        assert job.script is not None
        assert job.script["title"] == "t"
        assert job.cost_usd >= Decimal("0")
        assert job.progress["stage"] == "stub_render"

    async def test_creates_scenes_from_script(
        self, clean_db: AsyncSession, job_id: int, overridden_agent: None
    ) -> None:
        await run_video({"_test_no_sleep": True}, job_id)
        scenes = await SceneRepo(clean_db).list_by_job(job_id)
        assert len(scenes) == 3
        assert all(s.status == SceneStatus.DONE.value for s in scenes)
        assert [s.narration for s in scenes] == ["n0", "n1", "n2"]

    async def test_aborts_when_already_cancelled(
        self, clean_db: AsyncSession, job_id: int, overridden_agent: None
    ) -> None:
        await JobRepo(clean_db).update_status(job_id, JobStatus.CANCELLED)
        await clean_db.commit()
        await run_video({"_test_no_sleep": True}, job_id)
        job = await JobRepo(clean_db).get(job_id)
        assert job is not None
        assert job.status == JobStatus.CANCELLED.value
        assert await SceneRepo(clean_db).list_by_job(job_id) == []

    async def test_noop_when_job_missing(self, clean_db: AsyncSession) -> None:
        await run_video({"_test_no_sleep": True}, 9999)

    async def test_budget_violation_marks_failed(
        self, clean_db: AsyncSession, job_id: int
    ) -> None:
        oversized = _canned(n=20, total=60.0)
        with script_agent.override(model=TestModel(custom_output_args=oversized.model_dump())):
            await run_video({"_test_no_sleep": True}, job_id)
        job = await JobRepo(clean_db).get(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED.value
        assert job.error is not None
        assert job.error["type"] == "budget_exceeded"
        assert job.error["reason"] == "scene_count"
