from decimal import Decimal

from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from app.llm.manim_agent import ManimCode, generate_manim_code, manim_agent

models.ALLOW_MODEL_REQUESTS = False


async def test_generate_returns_code_and_cost() -> None:
    canned = ManimCode(
        code="from manim import *\n\nclass GeneratedScene(Scene):\n    def construct(self): pass"
    )
    with manim_agent.override(model=TestModel(custom_output_args=canned.model_dump())):
        result = await generate_manim_code(
            visual_prompt="v",
            narration="n",
            duration_seconds="5.00",
            model="anthropic/claude-sonnet-4.6",
        )
    assert "GeneratedScene(Scene)" in result.code
    assert result.model == "anthropic/claude-sonnet-4.6"
    assert result.cost_usd >= Decimal("0")


async def test_generate_passes_retry_context() -> None:
    canned = ManimCode(
        code="from manim import *\n\nclass GeneratedScene(Scene):\n    def construct(self): pass"
    )
    with manim_agent.override(model=TestModel(custom_output_args=canned.model_dump())):
        result = await generate_manim_code(
            visual_prompt="v",
            narration="n",
            duration_seconds="5.00",
            model="anthropic/claude-opus-4.8",
            prev_code="bad",
            stderr="NameError",
        )
    assert result.model == "anthropic/claude-opus-4.8"
