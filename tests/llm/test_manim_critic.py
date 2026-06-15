from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from app.llm.manim_critic import Critique, critic_agent, critique, static_gate

models.ALLOW_MODEL_REQUESTS = False

_GOOD = "from manim import *\n\nclass GeneratedScene(Scene):\n    def construct(self):\n        self.wait(1)\n"


def test_static_gate_rejects_syntax_error() -> None:
    ok, issues = static_gate("class GeneratedScene(Scene:\n  pass")
    assert ok is False
    assert any("syntax" in i.lower() for i in issues)


def test_static_gate_rejects_missing_scene_class() -> None:
    ok, issues = static_gate("from manim import *\n\nx = 1\n")
    assert ok is False


def test_static_gate_rejects_wrong_class_name() -> None:
    ok, _ = static_gate("from manim import *\n\nclass Foo(Scene):\n    def construct(self): pass")
    assert ok is False


def test_static_gate_accepts_good_code() -> None:
    ok, issues = static_gate(_GOOD)
    assert ok is True
    assert issues == []


async def test_critique_short_circuits_on_static_failure() -> None:
    result = await critique(code="def x(:", duration_seconds="5.00")
    assert result.ok is False
    assert result.cost_usd == 0


async def test_critique_runs_llm_when_static_passes() -> None:
    with critic_agent.override(model=TestModel(custom_output_args=Critique(ok=True, issues=[]).model_dump())):
        result = await critique(code=_GOOD, duration_seconds="5.00")
    assert result.ok is True
