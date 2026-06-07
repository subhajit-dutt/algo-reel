"""Manual TTS smoke. Hits the real OpenAI audio endpoint and writes a WAV locally.

Usage: make smoke-tts args="explain binary search in one sentence"
Requires ALGOREEL_ALLOW_LIVE_TTS=1 and a real OPENAI_API_KEY.
"""

import asyncio
import os
import sys
from pathlib import Path

from app.config import get_settings
from app.storage import LocalStorage
from app.tts.client import get_tts_client
from app.tts.synthesizer import synthesize_scene


async def main() -> int:
    if os.environ.get("ALGOREEL_ALLOW_LIVE_TTS") != "1":
        print("Refusing to run: set ALGOREEL_ALLOW_LIVE_TTS=1 to hit the live API.", file=sys.stderr)
        return 1
    narration = " ".join(sys.argv[1:]) or "Hello from algo-reel."
    s = get_settings()
    result = await synthesize_scene(
        narration=narration, voice=s.tts_voice_default, client=get_tts_client()
    )
    storage = LocalStorage(s.media_root)
    stored = await storage.put("smoke/tts.wav", result.audio_bytes, result.content_type)
    print(f"wrote {Path(s.media_root) / stored.key}")
    print(f"duration={result.duration_seconds}s cost=${result.cost_usd} bytes={stored.bytes}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
