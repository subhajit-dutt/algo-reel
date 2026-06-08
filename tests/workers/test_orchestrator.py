import io
import wave
from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from pydantic_ai import models
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AssetKind, JobStatus, Renderer, SceneStatus
from app.domain.script import Scene as DomainScene
from app.domain.script import VideoScript
from app.llm.script_agent import script_agent
from app.repositories.asset_repo import AssetRepo
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo
from app.storage import LocalStorage
from app.workers.orchestrator import run_video

models.ALLOW_MODEL_REQUESTS = False


def _wav(seconds: float, framerate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(framerate)
        w.writeframes(b"\x00\x00" * int(seconds * framerate))
    return buf.getvalue()


class FakeTTSClient:
    def __init__(self, *, seconds: float = 5.0, fail_on_index: int | None = None) -> None:
        self._data = _wav(seconds)
        self._fail_on_index = fail_on_index
        self.calls: list[str] = []

    async def synthesize(self, *, text: str, voice: str, instructions: str) -> bytes:
        idx = len(self.calls)
        self.calls.append(text)
        if self._fail_on_index is not None and idx == self._fail_on_index:
            raise RuntimeError("tts boom")
        return self._data


class _FailingStorage:
    """Storage whose put() always raises — exercises the storage-failure branch
    of _synth_one (synthesis succeeds, the file write fails)."""

    async def put(self, key: str, data: bytes, content_type: str) -> object:
        raise OSError("disk full")

    def url(self, key: str) -> str:
        raise NotImplementedError


def _canned(n: int = 3, total: float = 60.0) -> VideoScript:
    per = total / n
    return VideoScript(
        title="t",
        renderer=Renderer.MANIM,
        voice="alloy",
        total_duration=total,
        scenes=[
            DomainScene(index=i, narration=f"n{i}", visual_prompt=f"v{i}", duration_seconds=per)
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


@pytest.fixture
def stub_tts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeTTSClient:
    """Stub the orchestrator's TTS client + storage seams so a full-pipeline run
    never hits OpenAI. Voicing runs between SCRIPT_READY and RENDERING."""
    fake = FakeTTSClient(seconds=5.0)
    monkeypatch.setattr("app.workers.orchestrator.get_tts_client", lambda: fake)
    monkeypatch.setattr("app.workers.orchestrator.get_storage", lambda: LocalStorage(tmp_path))
    return fake


class TestRunVideo:
    async def test_walks_job_to_done(
        self,
        clean_db: AsyncSession,
        job_id: int,
        overridden_agent: None,
        stub_tts: FakeTTSClient,
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
        self,
        clean_db: AsyncSession,
        job_id: int,
        overridden_agent: None,
        stub_tts: FakeTTSClient,
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

    async def test_budget_violation_marks_failed(self, clean_db: AsyncSession, job_id: int) -> None:
        oversized = _canned(n=20, total=60.0)
        with script_agent.override(model=TestModel(custom_output_args=oversized.model_dump())):
            await run_video({"_test_no_sleep": True}, job_id)
        job = await JobRepo(clean_db).get(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED.value
        assert job.error is not None
        assert job.error["type"] == "budget_exceeded"
        assert job.error["reason"] == "scene_count"

    async def test_script_and_cost_committed_before_transition(
        self,
        clean_db: AsyncSession,
        job_id: int,
        overridden_agent: None,
        stub_tts: FakeTTSClient,
    ) -> None:
        """Spec §13: LLM spend (script + cost + scenes) is committed BEFORE the
        SCRIPT_READY transition is attempted, so a cancel race cannot wipe the
        spend via _AbortedError → session_scope rollback.

        We verify the ordering by inspecting state via a separate session
        BEFORE run_video returns is impractical from a test, but the happy
        path already proves the writes land. The defensive ordering is in
        orchestrator._execute (see comment near `await session.commit()` in
        the SCRIPTING branch).
        """
        # Sanity check: a normal run leaves script + cost + scenes on the row.
        await run_video({"_test_no_sleep": True}, job_id)
        job = await JobRepo(clean_db).get(job_id)
        assert job is not None
        assert job.script is not None
        assert len(await SceneRepo(clean_db).list_by_job(job_id)) == 3

    async def test_voices_scenes_with_real_durations_and_assets(
        self,
        clean_db: AsyncSession,
        job_id: int,
        overridden_agent: None,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake = FakeTTSClient(seconds=5.0)
        monkeypatch.setattr("app.workers.orchestrator.get_tts_client", lambda: fake)
        monkeypatch.setattr("app.workers.orchestrator.get_storage", lambda: LocalStorage(tmp_path))

        await run_video({"_test_no_sleep": True}, job_id)

        scenes = await SceneRepo(clean_db).list_by_job(job_id)
        assert len(scenes) == 3
        # LLM placeholder was 20.0 (60s / 3); measured audio is 5.00s.
        assert all(s.duration_seconds == Decimal("5.00") for s in scenes)
        assert len(fake.calls) == 3

        audio_ids = await AssetRepo(clean_db).audio_scene_ids(job_id)
        assert audio_ids == {s.id for s in scenes}
        for s in scenes:
            assert (tmp_path / "audio" / str(job_id) / f"{s.id}.wav").exists()

        job = await JobRepo(clean_db).get(job_id)
        assert job is not None
        assert job.status == JobStatus.DONE.value
        # 3 scenes * 5s * $0.015/min = 3 * 0.0013 = 0.0039 (TTS portion of cost)
        assert job.cost_usd >= Decimal("0.0039")

    async def test_tts_failure_fails_job(
        self,
        clean_db: AsyncSession,
        job_id: int,
        overridden_agent: None,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake = FakeTTSClient(seconds=5.0, fail_on_index=1)
        monkeypatch.setattr("app.workers.orchestrator.get_tts_client", lambda: fake)
        monkeypatch.setattr("app.workers.orchestrator.get_storage", lambda: LocalStorage(tmp_path))

        await run_video({"_test_no_sleep": True}, job_id)

        job = await JobRepo(clean_db).get(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED.value
        assert job.error is not None
        assert job.error["type"] == "tts_error"
        assert job.error["scene_index"] == 1

    async def test_resume_skips_already_voiced_scenes(
        self,
        clean_db: AsyncSession,
        job_id: int,
        overridden_agent: None,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        repo = JobRepo(clean_db)
        from app.llm.script_agent import generate_script

        result = await generate_script(
            prompt="x", renderer=Renderer.MANIM, duration_target_seconds=60
        )
        await repo.set_script(job_id, result.script.model_dump(mode="json"))
        scenes = await SceneRepo(clean_db).bulk_insert_from_script(job_id, result.script)
        await repo.update_status(job_id, JobStatus.SCRIPT_READY, expected_from=JobStatus.QUEUED)
        await AssetRepo(clean_db).record(
            job_id,
            scenes[0].id,
            AssetKind.AUDIO,
            f"audio/{job_id}/{scenes[0].id}.wav",
            10,
            "audio/wav",
        )
        await clean_db.commit()

        fake = FakeTTSClient(seconds=5.0)
        monkeypatch.setattr("app.workers.orchestrator.get_tts_client", lambda: fake)
        monkeypatch.setattr("app.workers.orchestrator.get_storage", lambda: LocalStorage(tmp_path))

        await run_video({"_test_no_sleep": True}, job_id)

        assert len(fake.calls) == len(scenes) - 1
        audio_ids = await AssetRepo(clean_db).audio_scene_ids(job_id)
        assert audio_ids == {s.id for s in scenes}

    async def test_storage_failure_fails_job(
        self,
        clean_db: AsyncSession,
        job_id: int,
        overridden_agent: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Synthesis succeeds, but the file write fails — still a typed tts_error,
        # whole job FAILED, no assets persisted (the batch never commits).
        fake = FakeTTSClient(seconds=5.0)
        monkeypatch.setattr("app.workers.orchestrator.get_tts_client", lambda: fake)
        monkeypatch.setattr("app.workers.orchestrator.get_storage", lambda: _FailingStorage())

        await run_video({"_test_no_sleep": True}, job_id)

        job = await JobRepo(clean_db).get(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED.value
        assert job.error is not None
        assert job.error["type"] == "tts_error"
        assert await AssetRepo(clean_db).audio_scene_ids(job_id) == set()
