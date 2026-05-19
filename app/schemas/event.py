from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.enums import JobStatus


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


class ProgressEvent(BaseModel):
    event: Literal["snapshot", "progress", "transition", "failed", "done", "cancelled"]
    job_id: int
    status: JobStatus
    progress: dict[str, Any]
    scene_id: int | None = None
    error: dict[str, Any] | None = None
    ts: datetime = Field(default_factory=_utc_now)
