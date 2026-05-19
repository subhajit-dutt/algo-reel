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
    if cost_usd > max_cost:
        raise BudgetExceededError("script_cost", cost_usd)
    n = len(script.scenes)
    if n < _MIN_SCENES or n > max_scenes:
        raise BudgetExceededError("scene_count", n)
    drift = abs(script.total_duration - target_seconds) / target_seconds
    if drift > _MAX_DRIFT:
        raise BudgetExceededError("duration_drift", drift)
