import io
import wave
from decimal import Decimal

_QUANT = Decimal("0.01")  # matches scenes.duration_seconds Numeric(6, 2)


def wav_duration_seconds(data: bytes) -> Decimal:
    """Read a WAV byte blob and return its duration in seconds, quantized to 0.01."""
    with wave.open(io.BytesIO(data), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
    if rate == 0:
        raise ValueError("wav framerate is zero")
    return (Decimal(frames) / Decimal(rate)).quantize(_QUANT)
