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
