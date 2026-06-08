import io
import wave
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Render
from app.domain.enums import AssetKind, Renderer, SceneStatus
from app.domain.script import Scene as DomainScene
from app.domain.script import VideoScript
from app.render.base import RenderError
from app.render.sandbox import RunResult
from app.repositories.asset_repo import AssetRepo
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo
from app.storage import LocalStorage
from app.workers.render import compose_video, render_scene


def _wav(seconds: float, framerate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(framerate)
        w.writeframes(b"\x00\x00" * int(seconds * framerate))
    return buf.getvalue()


class _FakeRenderer:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    async def render(self, *, job_id: int, render_in: object, input_dir: Path,
                     output_dir: Path) -> RunResult:
        self.calls += 1
        if self.fail:
            return RunResult(exit_code=1, stdout="", stderr="boom", timed_out=False)
        (output_dir / "scene.mp4").write_bytes(b"\x00FAKEMP4")
        return RunResult(exit_code=0, stdout="", stderr="", timed_out=False)


async def _seed_voiced_scene(session: AsyncSession, storage: LocalStorage) -> tuple[int, int]:
    job = await JobRepo(session).create(
        user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
    )
    await session.flush()
    script = VideoScript(
        title="t", renderer=Renderer.MANIM, voice="alloy", total_duration=5.0,
        scenes=[DomainScene(index=0, narration="hi", visual_prompt="v", duration_seconds=5.0)],
    )
    scenes = await SceneRepo(session).bulk_insert_from_script(job.id, script)
    sid = scenes[0].id
    key = f"audio/{job.id}/{sid}.wav"
    await storage.put(key, _wav(5.0), "audio/wav")
    await AssetRepo(session).record(job.id, sid, AssetKind.AUDIO, key, 123, "audio/wav")
    await session.commit()
    return job.id, sid


async def test_render_scene_produces_mp4(
    clean_db: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = LocalStorage(tmp_path)
    monkeypatch.setattr("app.workers.render.get_storage", lambda: storage)
    monkeypatch.setattr("app.workers.render.get_renderer", lambda: _FakeRenderer())
    job_id, sid = await _seed_voiced_scene(clean_db, storage)

    await render_scene({}, sid, 1)

    clean_db.expire_all()
    scene = await SceneRepo(clean_db).get(sid)
    assert scene is not None
    assert scene.status == SceneStatus.DONE.value
    assert scene.output_url is not None
    assert (tmp_path / "video" / str(job_id) / f"{sid}.mp4").exists()
    assert await AssetRepo(clean_db).storage_key_for(sid, AssetKind.SCENE_MP4) == (
        f"video/{job_id}/{sid}.mp4"
    )
    rows = (await clean_db.execute(select(Render).where(Render.scene_id == sid))).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "succeeded"
    assert rows[0].duration_ms is not None


async def test_render_scene_failure_marks_failed(
    clean_db: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = LocalStorage(tmp_path)
    monkeypatch.setattr("app.workers.render.get_storage", lambda: storage)
    monkeypatch.setattr("app.workers.render.get_renderer", lambda: _FakeRenderer(fail=True))
    _job_id, sid = await _seed_voiced_scene(clean_db, storage)

    with pytest.raises(RenderError):
        await render_scene({}, sid, 1)

    clean_db.expire_all()
    scene = await SceneRepo(clean_db).get(sid)
    assert scene is not None
    assert scene.status == SceneStatus.FAILED.value
    rows = (await clean_db.execute(select(Render).where(Render.scene_id == sid))).scalars().all()
    assert rows[0].status == "failed"
    assert rows[0].stderr == "boom"


async def test_render_scene_idempotent_skip(
    clean_db: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = LocalStorage(tmp_path)
    fake = _FakeRenderer()
    monkeypatch.setattr("app.workers.render.get_storage", lambda: storage)
    monkeypatch.setattr("app.workers.render.get_renderer", lambda: fake)
    _job_id, sid = await _seed_voiced_scene(clean_db, storage)
    await SceneRepo(clean_db).update_status(sid, SceneStatus.DONE)
    await clean_db.commit()

    await render_scene({}, sid, 1)
    assert fake.calls == 0


async def test_compose_video_concats(
    clean_db: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = LocalStorage(tmp_path)
    monkeypatch.setattr("app.workers.render.get_storage", lambda: storage)

    async def fake_runner(*, image: str, command: list[str], input_dir: Path,
                          output_dir: Path, limits: object, name: str) -> RunResult:
        (output_dir / "final.mp4").write_bytes(b"\x00FINAL")
        return RunResult(exit_code=0, stdout="", stderr="", timed_out=False)

    monkeypatch.setattr("app.workers.render.get_sandbox_runner", lambda: fake_runner)

    job = await JobRepo(clean_db).create(
        user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
    )
    await clean_db.flush()
    script = VideoScript(
        title="t", renderer=Renderer.MANIM, voice="alloy", total_duration=10.0,
        scenes=[
            DomainScene(index=i, narration=f"n{i}", visual_prompt="v", duration_seconds=5.0)
            for i in range(2)
        ],
    )
    scenes = await SceneRepo(clean_db).bulk_insert_from_script(job.id, script)
    for sc in scenes:
        key = f"video/{job.id}/{sc.id}.mp4"
        await storage.put(key, b"\x00SCENE", "video/mp4")
        await AssetRepo(clean_db).record(job.id, sc.id, AssetKind.SCENE_MP4, key, 6, "video/mp4")
    await clean_db.commit()
    job_id = job.id

    await compose_video({}, job_id)

    clean_db.expire_all()
    refreshed = await JobRepo(clean_db).get(job_id)
    assert refreshed is not None
    assert refreshed.output_url is not None
    assert (tmp_path / "video" / str(job_id) / "final.mp4").exists()
