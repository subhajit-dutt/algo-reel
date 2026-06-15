from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from app.domain.enums import Renderer
from app.render.sandbox import RunResult


@dataclass(frozen=True)
class RenderInput:
    scene_index: int
    text: str
    duration: Decimal
    visual_prompt: str = ""
    code: str = ""


class RenderError(Exception):
    def __init__(self, scene_index: int, stderr: str) -> None:
        super().__init__(stderr)
        self.scene_index = scene_index
        self.stderr = stderr


class SceneRenderer(Protocol):
    async def render(
        self, *, job_id: int, render_in: RenderInput, input_dir: Path, output_dir: Path
    ) -> RunResult: ...


def get_renderer(renderer: Renderer) -> SceneRenderer:
    # Lazy imports avoid base <-> concrete-renderer import cycles.
    if renderer is Renderer.MANIM:
        from app.render.manim import ManimRenderer

        return ManimRenderer()
    from app.render.trivial import TrivialRenderer

    return TrivialRenderer()
