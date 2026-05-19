from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import JobStatus, Renderer
from app.schemas.scene import SceneResponse


class CreateJobRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    renderer: Renderer
    duration_target: Literal[30, 60, 180]
    voice: str = Field(min_length=1, max_length=64, default="alloy")


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_prompt: str
    renderer: Renderer
    voice: str
    duration_target_seconds: int
    status: JobStatus
    progress: dict[str, Any]
    output_url: str | None
    cost_usd: Decimal
    error: dict[str, Any] | None
    scenes: list[SceneResponse]
    created_at: datetime
    updated_at: datetime
