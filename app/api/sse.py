import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.api.auth import require_bearer_token
from app.deps import get_job_service, get_redis
from app.domain.enums import JobStatus
from app.domain.state_machine import TERMINAL_JOB_STATUSES
from app.schemas.event import ProgressEvent
from app.services.job_service import JobNotFoundError, JobService
from app.services.progress_publisher import ProgressPublisher

router = APIRouter(
    prefix="/api/videos",
    tags=["videos"],
    dependencies=[Depends(require_bearer_token)],
)


@router.get("/{job_id}/events")
async def stream_events(
    job_id: int,
    service: JobService = Depends(get_job_service),
    redis: Any = Depends(get_redis),
) -> EventSourceResponse:
    try:
        job = await service.get_job(job_id)
    except JobNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    snapshot_status = JobStatus(job.status)
    snapshot = ProgressEvent(
        event="snapshot",
        job_id=job.id,
        status=snapshot_status,
        progress=job.progress,
        error=job.error,
        ts=datetime.now(tz=UTC),
    )

    async def _gen() -> AsyncIterator[dict[str, str]]:
        yield {"event": "snapshot", "data": snapshot.model_dump_json()}
        if snapshot_status in TERMINAL_JOB_STATUSES:
            return

        pubsub = redis.pubsub()
        await pubsub.subscribe(ProgressPublisher.channel(job_id))
        try:
            async for msg in pubsub.listen():
                if msg["type"] != "message":
                    continue
                data = msg["data"]
                yield {"event": "progress", "data": data}
                parsed = json.loads(data)
                if parsed.get("status") in {s.value for s in TERMINAL_JOB_STATUSES}:
                    return
        finally:
            await pubsub.unsubscribe()
            await pubsub.aclose()

    return EventSourceResponse(_gen(), ping=15)
