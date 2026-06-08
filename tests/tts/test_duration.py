import io
import wave
from decimal import Decimal

from app.tts.duration import wav_duration_seconds


def _make_wav(*, seconds: float, framerate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)  # 16-bit
        w.setframerate(framerate)
        w.writeframes(b"\x00\x00" * int(seconds * framerate))
    return buf.getvalue()


def test_measures_one_second() -> None:
    assert wav_duration_seconds(_make_wav(seconds=1.0)) == Decimal("1.00")


def test_measures_fractional_seconds() -> None:
    assert wav_duration_seconds(_make_wav(seconds=2.5)) == Decimal("2.50")


def test_quantizes_to_two_places() -> None:
    # 24001 frames @ 24000 Hz = 1.0000416... -> 1.00
    result = wav_duration_seconds(_make_wav(seconds=24001 / 24000))
    assert result == Decimal("1.00")
    assert result.as_tuple().exponent == -2
