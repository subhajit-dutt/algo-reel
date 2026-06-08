import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Render
from app.domain.enums import Renderer
from app.domain.script import Scene as DomainScene
from app.domain.script import VideoScript
from app.repositories.job_repo import JobRepo
from app.repositories.render_repo import RenderRepo
from app.repositories.scene_repo import SceneRepo


@pytest_asyncio.fixture
async def scene_id(clean_db: AsyncSession) -> int:
    job = await JobRepo(clean_db).create(
        user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=30
    )
    await clean_db.flush()
    script = VideoScript(
        title="t", renderer=Renderer.MANIM, voice="alloy", total_duration=10.0,
        scenes=[DomainScene(index=0, narration="n", visual_prompt="v", duration_seconds=10.0)],
    )
    scenes = await SceneRepo(clean_db).bulk_insert_from_script(job.id, script)
    await clean_db.commit()
    return scenes[0].id


async def test_start_then_succeed(clean_db: AsyncSession, scene_id: int) -> None:
    repo = RenderRepo(clean_db)
    render = await repo.start_attempt(scene_id, attempt=1)
    await repo.mark_succeeded(render.id, duration_ms=1234)
    await clean_db.commit()

    row = (await clean_db.execute(select(Render).where(Render.id == render.id))).scalar_one()
    assert row.status == "succeeded"
    assert row.duration_ms == 1234


async def test_start_then_fail(clean_db: AsyncSession, scene_id: int) -> None:
    repo = RenderRepo(clean_db)
    render = await repo.start_attempt(scene_id, attempt=1)
    await repo.mark_failed(render.id, stderr="boom")
    await clean_db.commit()

    row = (await clean_db.execute(select(Render).where(Render.id == render.id))).scalar_one()
    assert row.status == "failed"
    assert row.stderr == "boom"
