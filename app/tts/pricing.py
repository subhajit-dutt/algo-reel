from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


class UnknownModelError(Exception):
    pass


@dataclass(frozen=True)
class TTSPricing:
    per_minute_usd: Decimal


# Verify rate against OpenAI's current pricing page when bumping the model.
TTS_PRICING: dict[str, TTSPricing] = {
    "gpt-4o-mini-tts": TTSPricing(per_minute_usd=Decimal("0.015")),
}

_QUANT = Decimal("0.0001")


def compute_tts_cost(model: str, *, audio_seconds: Decimal) -> Decimal:
    if audio_seconds < 0:
        raise ValueError(f"audio_seconds must be non-negative: {audio_seconds}")
    if model not in TTS_PRICING:
        raise UnknownModelError(f"no pricing entry for tts model: {model}")
    rate = TTS_PRICING[model].per_minute_usd
    raw = (audio_seconds / Decimal(60)) * rate
    return raw.quantize(_QUANT, rounding=ROUND_HALF_UP)
