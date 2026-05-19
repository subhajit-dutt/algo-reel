from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from app.domain.enums import JobStatus


class ProgressEvent(BaseModel):
    event: Literal["snapshot", "progress", "transition", "failed", "done"]
    job_id: int
    status: JobStatus
    progress: dict[str, Any]
    scene_id: int | None = None
    error: dict[str, Any] | None = None
    ts: datetime
