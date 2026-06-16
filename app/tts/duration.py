import io
import wave
from decimal import Decimal

_QUANT = Decimal("0.01")  # matches scenes.duration_seconds Numeric(6, 2)


def wav_duration_seconds(data: bytes) -> Decimal:
    """Read a WAV byte blob and return its duration in seconds, quantized to 0.01.

    The header's declared frame count is not trusted: OpenAI streams WAV with a
    0xFFFFFFFF placeholder data-chunk size, so ``getnframes()`` reports ~2.1B
    frames. ``readframes`` is capped at the bytes actually present, so the true
    frame count is derived from the real payload regardless of the declared size.
    """
    with wave.open(io.BytesIO(data), "rb") as w:
        rate = w.getframerate()
        framesize = w.getnchannels() * w.getsampwidth()
        frames = len(w.readframes(w.getnframes())) // framesize
    if rate == 0:
        raise ValueError("wav framerate is zero")
    return (Decimal(frames) / Decimal(rate)).quantize(_QUANT)
