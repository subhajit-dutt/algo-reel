from decimal import Decimal

import pytest

from app.llm.pricing import (
    MODEL_PRICING,
    Pricing,
    UnknownModelError,
    compute_cost,
)


class TestComputeCost:
    def test_haiku_45_million_tokens_each(self) -> None:
        cost = compute_cost(
            "anthropic/claude-haiku-4.5",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        assert cost == Decimal("6.0000")

    def test_zero_usage_zero_cost(self) -> None:
        cost = compute_cost("anthropic/claude-haiku-4.5", input_tokens=0, output_tokens=0)
        assert cost == Decimal("0.0000")

    def test_unknown_model_raises(self) -> None:
        with pytest.raises(UnknownModelError):
            compute_cost("openrouter/unknown-model", input_tokens=100, output_tokens=100)

    def test_haiku_present_in_table(self) -> None:
        assert "anthropic/claude-haiku-4.5" in MODEL_PRICING
        p = MODEL_PRICING["anthropic/claude-haiku-4.5"]
        assert isinstance(p, Pricing)
        assert p.input_per_mtok > 0
        assert p.output_per_mtok > 0

    def test_result_quantized_four_decimals(self) -> None:
        cost = compute_cost("anthropic/claude-haiku-4.5", input_tokens=1234, output_tokens=567)
        assert cost.as_tuple().exponent == -4


def test_sonnet_codegen_pricing() -> None:
    # 1M input + 1M output at $3 / $15
    assert compute_cost(
        "anthropic/claude-sonnet-4.6", input_tokens=1_000_000, output_tokens=1_000_000
    ) == Decimal("18.0000")


def test_opus_retry_pricing() -> None:
    assert compute_cost(
        "anthropic/claude-opus-4.8", input_tokens=1_000_000, output_tokens=1_000_000
    ) == Decimal("30.0000")
