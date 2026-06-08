import io
import wave
from decimal import Decimal

from app.tts.synthesizer import SynthesisResult, synthesize_scene


def _wav(seconds: float, framerate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(framerate)
        w.writeframes(b"\x00\x00" * int(seconds * framerate))
    return buf.getvalue()


class _FakeTTSClient:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self.calls: list[dict[str, str]] = []

    async def synthesize(self, *, text: str, voice: str, instructions: str) -> bytes:
        self.calls.append({"text": text, "voice": voice, "instructions": instructions})
        return self._data


async def test_returns_duration_cost_and_content_type() -> None:
    client = _FakeTTSClient(_wav(3.0))
    result = await synthesize_scene(narration="hello world", voice="coral", client=client)
    assert isinstance(result, SynthesisResult)
    assert result.duration_seconds == Decimal("3.00")
    assert result.content_type == "audio/wav"
    # 3s @ $0.015/min = 0.00075 -> 0.0008 (ROUND_HALF_UP)
    assert result.cost_usd == Decimal("0.0008")
    assert result.audio_bytes == client._data


async def test_passes_narration_and_voice_to_client() -> None:
    client = _FakeTTSClient(_wav(1.0))
    await synthesize_scene(narration="the quick brown fox", voice="verse", client=client)
    assert client.calls[0]["text"] == "the quick brown fox"
    assert client.calls[0]["voice"] == "verse"
    assert client.calls[0]["instructions"]  # non-empty, from settings
