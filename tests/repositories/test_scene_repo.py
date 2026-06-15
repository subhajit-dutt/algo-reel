from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Renderer, SceneStatus
from app.domain.script import Scene as DomainScene
from app.domain.script import VideoScript
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo


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


class TestUpdateStatus:
    async def test_persists_new_status(self, clean_db) -> None:  # type: ignore[no-untyped-def]
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

        await repo.update_status(scenes[1].id, SceneStatus.DONE)
        await clean_db.commit()

        refetched = await repo.list_by_job(job.id)
        assert refetched[0].status == SceneStatus.PENDING.value
        assert refetched[1].status == SceneStatus.DONE.value
        assert refetched[2].status == SceneStatus.PENDING.value


async def test_set_duration_overwrites_placeholder(clean_db: AsyncSession) -> None:
    from decimal import Decimal

    from app.domain.enums import Renderer
    from app.domain.script import Scene as DomainScene
    from app.domain.script import VideoScript
    from app.repositories.job_repo import JobRepo
    from app.repositories.scene_repo import SceneRepo

    job = await JobRepo(clean_db).create(
        user_prompt="p", renderer=Renderer.MANIM, voice="coral", duration_target_seconds=30
    )
    await clean_db.flush()
    script = VideoScript(
        title="t",
        renderer=Renderer.MANIM,
        voice="coral",
        total_duration=10.0,
        scenes=[DomainScene(index=0, narration="n", visual_prompt="v", duration_seconds=10.0)],
    )
    repo = SceneRepo(clean_db)
    scenes = await repo.bulk_insert_from_script(job.id, script)
    await repo.set_duration(scenes[0].id, Decimal("4.25"))
    await clean_db.commit()

    refreshed = await repo.list_by_job(job.id)
    assert refreshed[0].duration_seconds == Decimal("4.25")


async def test_get_and_set_output_url(clean_db: AsyncSession) -> None:
    from app.domain.enums import Renderer, SceneStatus
    from app.domain.script import Scene as DomainScene
    from app.domain.script import VideoScript
    from app.repositories.job_repo import JobRepo
    from app.repositories.scene_repo import SceneRepo

    job = await JobRepo(clean_db).create(
        user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=30
    )
    await clean_db.flush()
    script = VideoScript(
        title="t",
        renderer=Renderer.MANIM,
        voice="alloy",
        total_duration=10.0,
        scenes=[DomainScene(index=0, narration="n", visual_prompt="v", duration_seconds=10.0)],
    )
    repo = SceneRepo(clean_db)
    scenes = await repo.bulk_insert_from_script(job.id, script)
    sid = scenes[0].id
    await repo.set_output_url(sid, "file:///x/scene.mp4")
    await clean_db.commit()

    got = await repo.get(sid)
    assert got is not None
    assert got.output_url == "file:///x/scene.mp4"
    assert got.status == SceneStatus.PENDING.value
    assert await repo.get(999999) is None


async def test_set_manim_code(clean_db) -> None:  # type: ignore[no-untyped-def]
    from app.domain.enums import Renderer
    from app.domain.script import Scene as DomainScene
    from app.domain.script import VideoScript
    from app.repositories.job_repo import JobRepo
    from app.repositories.scene_repo import SceneRepo

    job = await JobRepo(clean_db).create(
        user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
    )
    await clean_db.flush()
    scenes = await SceneRepo(clean_db).bulk_insert_from_script(
        job.id,
        VideoScript(
            title="t",
            renderer=Renderer.MANIM,
            voice="alloy",
            total_duration=5.0,
            scenes=[DomainScene(index=0, narration="n", visual_prompt="v", duration_seconds=5.0)],
        ),
    )
    sid = scenes[0].id
    await SceneRepo(clean_db).set_manim_code(sid, "code")
    await clean_db.commit()
    clean_db.expire_all()
    scene = await SceneRepo(clean_db).get(sid)
    assert scene is not None and scene.manim_code == "code"
