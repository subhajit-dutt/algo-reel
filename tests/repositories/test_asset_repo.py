import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AssetKind, Renderer
from app.domain.script import Scene as DomainScene
from app.domain.script import VideoScript
from app.repositories.asset_repo import AssetRepo
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo


def _script(n: int = 3) -> VideoScript:
    return VideoScript(
        title="t",
        renderer=Renderer.MANIM,
        voice="coral",
        total_duration=30.0,
        scenes=[
            DomainScene(index=i, narration=f"n{i}", visual_prompt=f"v{i}", duration_seconds=10.0)
            for i in range(n)
        ],
    )


@pytest_asyncio.fixture
async def seeded(clean_db: AsyncSession) -> tuple[int, list[int]]:
    job = await JobRepo(clean_db).create(
        user_prompt="p", renderer=Renderer.MANIM, voice="coral", duration_target_seconds=30
    )
    await clean_db.flush()
    scenes = await SceneRepo(clean_db).bulk_insert_from_script(job.id, _script())
    await clean_db.commit()
    return job.id, [s.id for s in scenes]


async def test_record_and_audio_scene_ids(
    clean_db: AsyncSession, seeded: tuple[int, list[int]]
) -> None:
    job_id, scene_ids = seeded
    repo = AssetRepo(clean_db)
    await repo.record(job_id, scene_ids[0], AssetKind.AUDIO, "audio/1/1.wav", 1234, "audio/wav")
    await clean_db.commit()

    assert await repo.audio_scene_ids(job_id) == {scene_ids[0]}


async def test_audio_scene_ids_empty_when_none(
    clean_db: AsyncSession, seeded: tuple[int, list[int]]
) -> None:
    job_id, _ = seeded
    assert await AssetRepo(clean_db).audio_scene_ids(job_id) == set()


async def test_storage_key_for(clean_db: AsyncSession, seeded: tuple[int, list[int]]) -> None:
    job_id, scene_ids = seeded
    repo = AssetRepo(clean_db)
    await repo.record(job_id, scene_ids[0], AssetKind.AUDIO, "audio/1/1.wav", 10, "audio/wav")
    await clean_db.commit()
    assert await repo.storage_key_for(scene_ids[0], AssetKind.AUDIO) == "audio/1/1.wav"
