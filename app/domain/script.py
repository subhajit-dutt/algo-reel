from pydantic import BaseModel, Field

from app.domain.enums import Renderer


class Scene(BaseModel):
    index: int = Field(ge=0)
    narration: str = Field(min_length=1, max_length=300)
    visual_prompt: str = Field(min_length=1)
    duration_seconds: float = Field(gt=0, allow_inf_nan=False)


class VideoScript(BaseModel):
    script_version: int = 1
    title: str = Field(min_length=1)
    renderer: Renderer
    voice: str = Field(min_length=1)
    total_duration: float = Field(gt=0, allow_inf_nan=False)
    scenes: list[Scene]
