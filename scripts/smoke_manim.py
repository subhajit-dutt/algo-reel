"""Gated live Manim render: renders a tiny canned scene through the real
algoreel-manim image and muxes a short silent wav. Requires Docker + the image.
Run: ALGOREEL_ALLOW_LIVE_RENDER=1 uv run python -m scripts.smoke_manim
"""

import asyncio
import os
import tempfile
import wave
from decimal import Decimal
from pathlib import Path

from app.render.base import RenderInput
from app.render.manim import ManimRenderer

_CODE = (
    "from manim import *\n\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    "        self.play(Write(Text('hello')), run_time=2)\n"
    "        self.wait(1)\n"
)


def _wav(path: Path, seconds: float = 3.0, rate: int = 24000) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))


async def main() -> None:
    if os.environ.get("ALGOREEL_ALLOW_LIVE_RENDER") != "1":
        raise SystemExit("refusing to run: set ALGOREEL_ALLOW_LIVE_RENDER=1")
    with tempfile.TemporaryDirectory() as in_s, tempfile.TemporaryDirectory() as out_s:
        in_dir, out_dir = Path(in_s), Path(out_s)
        _wav(in_dir / "audio.wav")
        result = await ManimRenderer().render(
            job_id=0,
            render_in=RenderInput(
                scene_index=0, text="hello", duration=Decimal("3.00"), code=_CODE
            ),
            input_dir=in_dir,
            output_dir=out_dir,
        )
        mp4 = out_dir / "scene.mp4"
        print("exit_code:", result.exit_code, "stderr:", result.stderr[-400:])
        print(
            "scene.mp4 exists:", mp4.exists(), "bytes:", mp4.stat().st_size if mp4.exists() else 0
        )
        assert result.exit_code == 0 and mp4.exists() and mp4.stat().st_size > 0


if __name__ == "__main__":
    asyncio.run(main())
