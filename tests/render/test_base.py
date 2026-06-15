from decimal import Decimal

from app.render.base import RenderInput


def test_render_input_carries_code_and_visual_prompt() -> None:
    ri = RenderInput(scene_index=0, text="n", duration=Decimal("5.00"), visual_prompt="v", code="c")
    assert ri.visual_prompt == "v"
    assert ri.code == "c"


def test_render_input_defaults_are_empty() -> None:
    ri = RenderInput(scene_index=0, text="n", duration=Decimal("5.00"))
    assert ri.visual_prompt == ""
    assert ri.code == ""


def test_get_renderer_defaults_to_trivial_for_ai_image() -> None:
    from app.domain.enums import Renderer
    from app.render.base import get_renderer
    from app.render.trivial import TrivialRenderer

    assert isinstance(get_renderer(Renderer.AI_IMAGE), TrivialRenderer)


def test_get_renderer_returns_manim_for_manim() -> None:
    from app.domain.enums import Renderer
    from app.render.base import get_renderer
    from app.render.manim import ManimRenderer

    assert isinstance(get_renderer(Renderer.MANIM), ManimRenderer)
