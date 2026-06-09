from pathlib import Path

from app.config import get_settings
from app.render.base import RenderInput
from app.render.sandbox import RunResult, SandboxLimits, get_sandbox_runner


class TrivialRenderer:
    """Renders a scene as a solid-background card with the narration drawn on it,
    pinned to the scene's measured audio duration, with that audio muxed in.
    The audio is staged at `input_dir/audio.wav` by the caller (render_scene)."""

    async def render(
        self, *, job_id: int, render_in: RenderInput, input_dir: Path, output_dir: Path
    ) -> RunResult:
        s = get_settings()
        (input_dir / "text.txt").write_text(render_in.text)
        limits = SandboxLimits(
            memory=s.render_memory,
            cpus=s.render_cpus,
            pids_limit=s.render_pids_limit,
            timeout_seconds=s.render_timeout_seconds,
            user=s.render_user,
        )
        drawtext = (
            "drawtext=fontfile=/opt/font.ttf:textfile=/in/text.txt:"
            "fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2:line_spacing=14"
        )
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={s.render_bg_color}:s={s.render_video_size}:r={s.render_video_fps}",
            "-i",
            "/in/audio.wav",
            "-vf",
            drawtext,
            "-t",
            str(render_in.duration),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "/out/scene.mp4",
        ]
        runner = get_sandbox_runner()
        return await runner(
            image=s.render_image,
            command=command,
            input_dir=input_dir,
            output_dir=output_dir,
            limits=limits,
            name=f"algoreel-render-{job_id}-{render_in.scene_index}",
        )
