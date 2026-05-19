from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.domain.enums import SceneStatus


class SceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    index: int
    narration: str
    visual_prompt: str
    duration_seconds: Decimal
    status: SceneStatus
    output_url: str | None
    created_at: datetime
    updated_at: datetime
