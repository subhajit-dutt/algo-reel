import asyncio
import io
import json
import wave
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from app.domain.enums import JobStatus, Renderer
from app.domain.script import Scene as DomainScene
from app.domain.script import VideoScript
from app.llm.script_agent import script_agent
from app.main import create_app
from app.render.sandbox import RunResult
from app.repositories.job_repo import JobRepo
from app.schemas.event import ProgressEvent
from app.services.progress_publisher import ProgressPublisher
from app.storage import LocalStorage
from app.workers.orchestrator import run_video
from app.workers.render import compose_video, render_scene
from tests.fakes import FakeArqPool


@pytest_asyncio.fixture
async def client(clean_db) -> AsyncIterator[AsyncClient]:  # type: ignore[no-untyped-def]
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers.update({"Authorization": "Bearer test-secret-123"})
            yield ac


def _parse_events(chunk: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in chunk.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data:"):
                events.append(json.loads(line[len("data:") :].strip()))
    return events


def _canned_script(n: int = 3, total: float = 60.0) -> VideoScript:
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


class _FakeTTSClient:
    def __init__(self, seconds: float = 5.0) -> None:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(b"\x00\x00" * int(seconds * 24000))
        self._data = buf.getvalue()

    async def synthesize(self, *, text: str, voice: str, instructions: str) -> bytes:
        return self._data


class TestSseEvents:
    async def test_returns_404_when_job_missing(self, client: AsyncClient) -> None:
        r = await client.get("/api/videos/9999/events")
        assert r.status_code == 404

    async def test_unauthorized_without_token(self, clean_db) -> None:  # type: ignore[no-untyped-def]
        app = create_app()
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                r = await ac.get("/api/videos/1/events")
                assert r.status_code == 401

    async def test_snapshot_then_close_when_terminal(self, client: AsyncClient, clean_db) -> None:  # type: ignore[no-untyped-def]
        repo = JobRepo(clean_db)
        job = await repo.create(
            user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
        )
        await repo.update_status(job.id, JobStatus.DONE)
        await clean_db.commit()

        async with client.stream("GET", f"/api/videos/{job.id}/events") as r:
            assert r.status_code == 200
            body = ""
            async for chunk in r.aiter_text():
                body += chunk
        events = _parse_events(body)
        assert events
        assert events[0]["event"] == "snapshot"
        assert events[0]["status"] == "done"

    async def test_snapshot_then_live_event(
        self, client: AsyncClient, clean_db, redis_client
    ) -> None:  # type: ignore[no-untyped-def]
        repo = JobRepo(clean_db)
        job = await repo.create(
            user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
        )
        await clean_db.commit()
        job_id = job.id

        publisher = ProgressPublisher(redis_client)

        async def _publish_after_delay() -> None:
            await asyncio.sleep(0.2)
            await publisher.publish(
                ProgressEvent(
                    event="transition",
                    job_id=job_id,
                    status=JobStatus.SCRIPTING,
                    progress={},
                    ts=datetime.now(tz=UTC),
                )
            )
            await asyncio.sleep(0.1)
            await publisher.publish(
                ProgressEvent(
                    event="done",
                    job_id=job_id,
                    status=JobStatus.DONE,
                    progress={},
                    ts=datetime.now(tz=UTC),
                )
            )

        result: dict[str, str] = {}

        async def _stream() -> None:
            async with client.stream("GET", f"/api/videos/{job_id}/events") as r:
                assert r.status_code == 200
                body = ""
                async for chunk in r.aiter_text():
                    body += chunk
                result["body"] = body

        await asyncio.gather(_publish_after_delay(), _stream())
        events = _parse_events(result["body"])
        kinds = [e["event"] for e in events]
        assert kinds[0] == "snapshot"
        assert "transition" in kinds
        assert kinds[-1] == "done"

    async def test_sse_event_name_matches_payload_event(
        self, client: AsyncClient, clean_db, redis_client
    ) -> None:  # type: ignore[no-untyped-def]
        """SSE 'event:' line must mirror the underlying ProgressEvent.event so that
        EventSource.addEventListener('done', ...) etc. dispatches correctly."""
        repo = JobRepo(clean_db)
        job = await repo.create(
            user_prompt="p", renderer=Renderer.MANIM, voice="alloy", duration_target_seconds=60
        )
        await clean_db.commit()
        job_id = job.id

        publisher = ProgressPublisher(redis_client)

        async def _publish() -> None:
            await asyncio.sleep(0.2)
            await publisher.publish(
                ProgressEvent(
                    event="failed",
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    progress={},
                    error={"type": "llm_error", "message": "boom"},
                    ts=datetime.now(tz=UTC),
                )
            )

        result: dict[str, str] = {}

        async def _stream() -> None:
            async with client.stream("GET", f"/api/videos/{job_id}/events") as r:
                body = ""
                async for chunk in r.aiter_text():
                    body += chunk
                result["body"] = body

        await asyncio.gather(_publish(), _stream())
        body = result["body"]
        # SSE wire format: lines like `event: failed\ndata: {...}\n\n`. Check the
        # event:-line names — not just the JSON-body events.
        event_lines = [line for line in body.splitlines() if line.startswith("event:")]
        assert any(line.strip() == "event: snapshot" for line in event_lines)
        assert any(line.strip() == "event: failed" for line in event_lines)

    async def test_e2e_pipeline_emits_tts_progress_events(
        self,
        client: AsyncClient,
        clean_db,  # type: ignore[no-untyped-def]
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Full pipeline run emits stage=tts progress events on the SSE stream
        between the script_ready transition and the rendering transition."""
        models.ALLOW_MODEL_REQUESTS = False
        monkeypatch.setattr("app.workers.orchestrator.get_tts_client", lambda: _FakeTTSClient())
        monkeypatch.setattr("app.workers.orchestrator.get_storage", lambda: LocalStorage(tmp_path))
        monkeypatch.setattr("app.workers.render.get_storage", lambda: LocalStorage(tmp_path))

        class _FakeRenderer:
            async def render(self, *, job_id, render_in, input_dir, output_dir):  # type: ignore[no-untyped-def]
                (output_dir / "scene.mp4").write_bytes(b"\x00FAKEMP4")
                return RunResult(exit_code=0, stdout="", stderr="", timed_out=False)

        monkeypatch.setattr("app.workers.render.get_renderer", lambda renderer: _FakeRenderer())

        from decimal import Decimal

        from app.llm.manim_agent import ManimCodeResult
        from app.llm.manim_critic import CritiqueResult

        async def _fake_codegen(
            *, visual_prompt, narration, duration_seconds, model, prev_code=None, stderr=None
        ):  # type: ignore[no-untyped-def]
            return ManimCodeResult(
                code="from manim import *\n\nclass GeneratedScene(Scene):\n    def construct(self): self.wait(1)\n",
                cost_usd=Decimal("0.01"),
                model=model,
            )

        async def _fake_critique(*, code, duration_seconds):  # type: ignore[no-untyped-def]
            return CritiqueResult(ok=True, issues=[], cost_usd=Decimal("0"))

        monkeypatch.setattr("app.workers.render.generate_manim_code", _fake_codegen)
        monkeypatch.setattr("app.workers.render.critique", _fake_critique)

        async def _fake_runner(*, image, command, input_dir, output_dir, limits, name):  # type: ignore[no-untyped-def]
            (output_dir / "final.mp4").write_bytes(b"\x00FINAL")
            return RunResult(exit_code=0, stdout="", stderr="", timed_out=False)

        monkeypatch.setattr("app.workers.render.get_sandbox_runner", lambda: _fake_runner)

        pool = FakeArqPool({"render_scene": render_scene, "compose_video": compose_video})

        repo = JobRepo(clean_db)
        job = await repo.create(
            user_prompt="hello",
            renderer=Renderer.MANIM,
            voice="alloy",
            duration_target_seconds=60,
        )
        await clean_db.commit()
        job_id = job.id

        result: dict[str, str] = {}

        async def _stream() -> None:
            async with client.stream("GET", f"/api/videos/{job_id}/events") as r:
                assert r.status_code == 200
                body = ""
                async for chunk in r.aiter_text():
                    body += chunk
                result["body"] = body

        with script_agent.override(
            model=TestModel(custom_output_args=_canned_script().model_dump())
        ):
            await asyncio.gather(
                _stream(),
                run_video({"redis": pool}, job_id),
            )

        collected = _parse_events(result["body"])

        tts_events = [
            e
            for e in collected
            if e.get("event") == "progress" and e.get("progress", {}).get("stage") == "tts"  # type: ignore[union-attr]
        ]
        assert tts_events, "expected at least one stage=tts progress event"
        assert all(e["status"] == "script_ready" for e in tts_events)
        render_events = [
            e
            for e in collected
            if e.get("event") == "progress" and e.get("progress", {}).get("stage") == "render"  # type: ignore[union-attr]
        ]
        compose_events = [
            e
            for e in collected
            if e.get("event") == "progress" and e.get("progress", {}).get("stage") == "compose"  # type: ignore[union-attr]
        ]
        assert render_events, "expected stage=render progress events"
        assert compose_events, "expected a stage=compose progress event"
        assert all(e["status"] == "rendering" for e in render_events)
        assert collected[-1]["event"] == "done"
