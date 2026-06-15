from pathlib import Path

from app.config import get_settings
from app.render.base import RenderInput
from app.render.sandbox import RunResult, SandboxLimits, get_sandbox_runner

# Manim renders at medium quality (720p30) into a known media dir; we render the
# class by its pinned name so the output path is deterministic. The audio is muxed
# in a second pass, pinned to the scene's measured duration (audio-first, spec D1).
_SCENE_NAME = "GeneratedScene"


class ManimRenderer:
    """Runs untrusted LLM-generated Manim code in the hardened sandbox, then muxes
    the pre-generated narration audio. The code is staged at input_dir/scene.py and
    the audio at input_dir/audio.wav by the caller (render_scene)."""

    async def render(
        self, *, job_id: int, render_in: RenderInput, input_dir: Path, output_dir: Path
    ) -> RunResult:
        s = get_settings()
        (input_dir / "scene.py").write_text(render_in.code)
        limits = SandboxLimits(
            memory=s.render_memory,
            cpus=s.render_cpus,
            pids_limit=s.render_pids_limit,
            timeout_seconds=s.manim_render_timeout_seconds,
            user=s.render_user,
            tmpfs_size=s.manim_tmpfs_size,
            env=(
                ("HOME", "/tmp"),
                ("XDG_CACHE_HOME", "/tmp/.cache"),
                ("MPLCONFIGDIR", "/tmp/.mpl"),
            ),
        )
        runner = get_sandbox_runner()

        manim_cmd = [
            "manim",
            "render",
            "-qm",
            "--media_dir",
            "/out/m",
            "--output_file",
            _SCENE_NAME,
            "/in/scene.py",
            _SCENE_NAME,
        ]
        manim_result = await runner(
            image=s.manim_image,
            command=manim_cmd,
            input_dir=input_dir,
            output_dir=output_dir,
            limits=limits,
            name=f"algoreel-manim-{job_id}-{render_in.scene_index}",
        )
        if manim_result.exit_code != 0 or manim_result.timed_out:
            return manim_result

        silent = next(output_dir.glob(f"m/videos/**/{_SCENE_NAME}.mp4"), None)
        if silent is None:
            return RunResult(
                exit_code=1,
                stdout=manim_result.stdout,
                stderr="manim produced no mp4",
                timed_out=False,
            )
        silent_in_container = "/out/" + str(silent.relative_to(output_dir))

        mux_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            silent_in_container,
            "-i",
            "/in/audio.wav",
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
        # Mux on the lean alpine render image (ffmpeg on PATH) rather than the heavy manim image.
        mux_limits = SandboxLimits(
            memory=s.render_memory,
            cpus=s.render_cpus,
            pids_limit=s.render_pids_limit,
            timeout_seconds=s.render_timeout_seconds,
            user=s.render_user,
        )
        return await runner(
            image=s.render_image,
            command=mux_cmd,
            input_dir=input_dir,
            output_dir=output_dir,
            limits=mux_limits,
            name=f"algoreel-mux-{job_id}-{render_in.scene_index}",
        )
