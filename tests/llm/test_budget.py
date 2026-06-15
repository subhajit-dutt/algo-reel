from decimal import Decimal

import pytest

from app.domain.enums import Renderer
from app.domain.script import Scene, VideoScript
from app.llm.budget import BudgetExceededError, enforce_budget


def _script(*, scenes: int, total: float) -> VideoScript:
    per = total / scenes
    return VideoScript(
        title="t",
        renderer=Renderer.MANIM,
        voice="alloy",
        total_duration=total,
        scenes=[
            Scene(index=i, narration="n", visual_prompt="v", duration_seconds=per)
            for i in range(scenes)
        ],
    )


class TestEnforceBudget:
    def test_happy_path(self) -> None:
        enforce_budget(
            _script(scenes=4, total=60.0),
            cost_usd=Decimal("0.01"),
            target_seconds=60,
            max_cost=Decimal("0.10"),
            max_scenes=12,
        )

    def test_cost_exceeded(self) -> None:
        with pytest.raises(BudgetExceededError) as exc:
            enforce_budget(
                _script(scenes=4, total=60.0),
                cost_usd=Decimal("0.50"),
                target_seconds=60,
                max_cost=Decimal("0.10"),
                max_scenes=12,
            )
        assert exc.value.reason == "script_cost"

    def test_scene_count_too_high(self) -> None:
        with pytest.raises(BudgetExceededError) as exc:
            enforce_budget(
                _script(scenes=20, total=60.0),
                cost_usd=Decimal("0.01"),
                target_seconds=60,
                max_cost=Decimal("0.10"),
                max_scenes=12,
            )
        assert exc.value.reason == "scene_count"

    def test_scene_count_too_low(self) -> None:
        with pytest.raises(BudgetExceededError) as exc:
            enforce_budget(
                _script(scenes=2, total=60.0),
                cost_usd=Decimal("0.01"),
                target_seconds=60,
                max_cost=Decimal("0.10"),
                max_scenes=12,
            )
        assert exc.value.reason == "scene_count"

    def test_duration_drift_too_high(self) -> None:
        with pytest.raises(BudgetExceededError) as exc:
            enforce_budget(
                _script(scenes=4, total=90.0),
                cost_usd=Decimal("0.01"),
                target_seconds=60,
                max_cost=Decimal("0.10"),
                max_scenes=12,
            )
        assert exc.value.reason == "duration_drift"

    def test_drift_at_boundary_passes(self) -> None:
        enforce_budget(
            _script(scenes=4, total=72.0),
            cost_usd=Decimal("0.01"),
            target_seconds=60,
            max_cost=Decimal("0.10"),
            max_scenes=12,
        )


def test_enforce_render_budget_raises_over_cap() -> None:
    from decimal import Decimal

    import pytest

    from app.llm.budget import RenderBudgetExceededError, enforce_render_budget

    enforce_render_budget(spent=Decimal("1.40"), cap=Decimal("1.50"))  # under cap: no raise
    with pytest.raises(RenderBudgetExceededError):
        enforce_render_budget(spent=Decimal("1.60"), cap=Decimal("1.50"))
