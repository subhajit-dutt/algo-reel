import io
import struct
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


def _streamed_wav(*, seconds: float, framerate: int = 24000) -> bytes:
    """A WAV whose RIFF and data chunk sizes are the 0xFFFFFFFF streaming
    placeholder, as emitted by OpenAI's TTS — the declared frame count is bogus
    while the actual audio payload is correct."""
    raw = bytearray(_make_wav(seconds=seconds, framerate=framerate))
    struct.pack_into("<I", raw, 4, 0xFFFFFFFF)  # RIFF chunk size
    struct.pack_into("<I", raw, 40, 0xFFFFFFFF)  # data sub-chunk size
    return bytes(raw)


def test_measures_one_second() -> None:
    assert wav_duration_seconds(_make_wav(seconds=1.0)) == Decimal("1.00")


def test_measures_fractional_seconds() -> None:
    assert wav_duration_seconds(_make_wav(seconds=2.5)) == Decimal("2.50")


def test_quantizes_to_two_places() -> None:
    # 24001 frames @ 24000 Hz = 1.0000416... -> 1.00
    result = wav_duration_seconds(_make_wav(seconds=24001 / 24000))
    assert result == Decimal("1.00")
    assert result.as_tuple().exponent == -2


def test_streamed_placeholder_header_uses_actual_payload() -> None:
    # OpenAI streams WAV with a 0xFFFFFFFF placeholder data size, so the header's
    # frame count is ~2.1B. Duration must come from the real payload, not the header.
    assert wav_duration_seconds(_streamed_wav(seconds=1.0)) == Decimal("1.00")
    assert wav_duration_seconds(_streamed_wav(seconds=2.5)) == Decimal("2.50")
