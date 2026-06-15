from decimal import Decimal

from app.domain.script import VideoScript

_MIN_SCENES = 3
_MAX_DRIFT = 0.20


class BudgetExceededError(Exception):
    def __init__(self, reason: str, value: object) -> None:
        super().__init__(f"budget exceeded: {reason}={value}")
        self.reason = reason
        self.value = value


def enforce_budget(
    script: VideoScript,
    *,
    cost_usd: Decimal,
    target_seconds: int,
    max_cost: Decimal,
    max_scenes: int,
) -> None:
    if target_seconds <= 0:
        raise ValueError(f"target_seconds must be positive, got {target_seconds}")
    if cost_usd > max_cost:
        raise BudgetExceededError("script_cost", cost_usd)
    n = len(script.scenes)
    if n < _MIN_SCENES or n > max_scenes:
        raise BudgetExceededError("scene_count", n)
    drift = abs(script.total_duration - target_seconds) / target_seconds
    if drift > _MAX_DRIFT:
        raise BudgetExceededError("duration_drift", drift)


class RenderBudgetExceededError(Exception):
    def __init__(self, spent: Decimal, cap: Decimal) -> None:
        super().__init__(f"render budget exceeded: spent={spent} cap={cap}")
        self.spent = spent
        self.cap = cap


def enforce_render_budget(*, spent: Decimal, cap: Decimal) -> None:
    if spent > cap:
        raise RenderBudgetExceededError(spent, cap)
