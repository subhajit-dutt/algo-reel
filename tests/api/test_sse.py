import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.domain.enums import JobStatus, Renderer
from app.main import create_app
from app.repositories.job_repo import JobRepo
from app.schemas.event import ProgressEvent
from app.services.progress_publisher import ProgressPublisher


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
