from dataclasses import dataclass
from decimal import Decimal

from app.config import get_settings
from app.tts.client import TTSClient
from app.tts.duration import wav_duration_seconds
from app.tts.pricing import compute_tts_cost

_CONTENT_TYPE = {"wav": "audio/wav", "mp3": "audio/mpeg"}


@dataclass(frozen=True)
class SynthesisResult:
    audio_bytes: bytes
    content_type: str
    duration_seconds: Decimal
    cost_usd: Decimal


async def synthesize_scene(*, narration: str, voice: str, client: TTSClient) -> SynthesisResult:
    """Synthesize one scene's narration. Raises on TTS failure after the client's retries."""
    s = get_settings()
    audio = await client.synthesize(text=narration, voice=voice, instructions=s.tts_instructions)
    duration = wav_duration_seconds(audio)
    cost = compute_tts_cost(s.tts_model, audio_seconds=duration)
    return SynthesisResult(
        audio_bytes=audio,
        content_type=_CONTENT_TYPE[s.tts_response_format],
        duration_seconds=duration,
        cost_usd=cost,
    )
