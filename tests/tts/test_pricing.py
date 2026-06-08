from decimal import Decimal

import pytest

from app.tts.pricing import UnknownModelError, compute_tts_cost


def test_cost_for_one_minute() -> None:
    # 60s at $0.015/min = $0.0150
    assert compute_tts_cost("gpt-4o-mini-tts", audio_seconds=Decimal("60")) == Decimal("0.0150")


def test_cost_rounds_half_up_to_four_places() -> None:
    # 5s at $0.015/min = 0.00125 -> 0.0013 (ROUND_HALF_UP)
    assert compute_tts_cost("gpt-4o-mini-tts", audio_seconds=Decimal("5")) == Decimal("0.0013")


def test_zero_seconds_is_zero() -> None:
    assert compute_tts_cost("gpt-4o-mini-tts", audio_seconds=Decimal("0")) == Decimal("0.0000")


def test_unknown_model_raises() -> None:
    with pytest.raises(UnknownModelError):
        compute_tts_cost("no-such-tts", audio_seconds=Decimal("10"))
