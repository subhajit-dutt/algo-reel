from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


class UnknownModelError(Exception):
    pass


@dataclass(frozen=True)
class Pricing:
    input_per_mtok: Decimal
    output_per_mtok: Decimal


MODEL_PRICING: dict[str, Pricing] = {
    "anthropic/claude-haiku-4.5": Pricing(
        input_per_mtok=Decimal("1.00"),
        output_per_mtok=Decimal("5.00"),
    ),
}


_QUANT = Decimal("0.0001")


def compute_cost(model: str, *, input_tokens: int, output_tokens: int) -> Decimal:
    if model not in MODEL_PRICING:
        raise UnknownModelError(f"no pricing entry for model: {model}")
    p = MODEL_PRICING[model]
    raw = (
        Decimal(input_tokens) * p.input_per_mtok + Decimal(output_tokens) * p.output_per_mtok
    ) / Decimal(1_000_000)
    return raw.quantize(_QUANT, rounding=ROUND_HALF_UP)
