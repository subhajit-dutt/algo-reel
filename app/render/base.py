from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from app.render.sandbox import RunResult


@dataclass(frozen=True)
class RenderInput:
    scene_index: int
    text: str
    duration: Decimal


class RenderError(Exception):
    def __init__(self, scene_index: int, stderr: str) -> None:
        super().__init__(stderr)
        self.scene_index = scene_index
        self.stderr = stderr


class SceneRenderer(Protocol):
    async def render(
        self, *, job_id: int, render_in: RenderInput, input_dir: Path, output_dir: Path
    ) -> RunResult: ...


def get_renderer() -> SceneRenderer:
    # Lazy import avoids a base <-> trivial import cycle (trivial imports RenderInput).
    from app.render.trivial import TrivialRenderer

    return TrivialRenderer()
