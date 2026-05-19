from pydantic import BaseModel

from app.domain.enums import Renderer


class Scene(BaseModel):
    index: int
    narration: str
    visual_prompt: str
    duration_seconds: float


class VideoScript(BaseModel):
    title: str
    renderer: Renderer
    voice: str
    total_duration: float
    scenes: list[Scene]
