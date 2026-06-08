"""Manual render smoke. Builds inputs, runs the real sandboxed renderer + compose
against Docker, and writes a final MP4 under MEDIA_ROOT.

Usage: make smoke-render
Requires ALGOREEL_ALLOW_LIVE_RENDER=1, a built `algoreel-render:m4` image, and Docker.
"""

import asyncio
import io
import os
import sys
import wave
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from app.config import get_settings
from app.render.base import RenderInput
from app.render.sandbox import SandboxLimits, get_sandbox_runner
from app.render.trivial import TrivialRenderer


def _silent_wav(seconds: float, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return buf.getvalue()


async def _main() -> None:
    if os.environ.get("ALGOREEL_ALLOW_LIVE_RENDER") != "1":
        print("Refusing to run: set ALGOREEL_ALLOW_LIVE_RENDER=1 to hit Docker.")
        sys.exit(1)
    s = get_settings()
    out_root = Path(s.media_root) / "smoke"
    out_root.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory() as in_s, TemporaryDirectory() as out_s:
        in_dir, out_dir = Path(in_s), Path(out_s)
        (in_dir / "audio.wav").write_bytes(_silent_wav(3.0))
        result = await TrivialRenderer().render(
            job_id=0,
            render_in=RenderInput(scene_index=0, text="algo-reel smoke render", duration=Decimal("3.00")),
            input_dir=in_dir,
            output_dir=out_dir,
        )
        if result.exit_code != 0:
            print(f"render failed: {result.stderr}")
            sys.exit(1)
        scene_mp4 = out_root / "scene.mp4"
        scene_mp4.write_bytes((out_dir / "scene.mp4").read_bytes())

    # Compose a single-scene final via the same runner.
    with TemporaryDirectory() as in_s, TemporaryDirectory() as out_s:
        in_dir, out_dir = Path(in_s), Path(out_s)
        (in_dir / "0.mp4").write_bytes(scene_mp4.read_bytes())
        (in_dir / "list.txt").write_text("file '/in/0.mp4'\n")
        limits = SandboxLimits(
            memory=s.render_memory, cpus=s.render_cpus, pids_limit=s.render_pids_limit,
            timeout_seconds=s.render_timeout_seconds, user=s.render_user,
        )
        result = await get_sandbox_runner()(
            image=s.render_image,
            command=["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "/in/list.txt",
                     "-c", "copy", "/out/final.mp4"],
            input_dir=in_dir, output_dir=out_dir, limits=limits, name="algoreel-smoke-compose",
        )
        if result.exit_code != 0:
            print(f"compose failed: {result.stderr}")
            sys.exit(1)
        final = out_root / "final.mp4"
        final.write_bytes((out_dir / "final.mp4").read_bytes())
        print(f"wrote {final} ({final.stat().st_size} bytes)")


if __name__ == "__main__":
    asyncio.run(_main())
