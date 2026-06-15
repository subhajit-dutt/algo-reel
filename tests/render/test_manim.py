from decimal import Decimal
from pathlib import Path

import pytest

from app.render.base import RenderInput
from app.render.sandbox import RunResult


async def test_manim_renderer_runs_manim_then_muxes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.render.manim import ManimRenderer

    calls: list[list[str]] = []

    async def fake_runner(*, image, command, input_dir, output_dir, limits, name):  # type: ignore[no-untyped-def]
        calls.append(command)
        if command[0] == "manim":
            silent = output_dir / "m" / "videos" / "scene" / "720p30" / "GeneratedScene.mp4"
            silent.parent.mkdir(parents=True, exist_ok=True)
            silent.write_bytes(b"\x00SILENT")
            return RunResult(exit_code=0, stdout="", stderr="", timed_out=False)
        (output_dir / "scene.mp4").write_bytes(b"\x00MUXED")
        return RunResult(exit_code=0, stdout="", stderr="", timed_out=False)

    monkeypatch.setattr("app.render.manim.get_sandbox_runner", lambda: fake_runner)

    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()
    (in_dir / "audio.wav").write_bytes(b"RIFF")

    renderer = ManimRenderer()
    result = await renderer.render(
        job_id=7,
        render_in=RenderInput(
            scene_index=2,
            text="n",
            duration=Decimal("5.00"),
            visual_prompt="v",
            code="from manim import *\n\nclass GeneratedScene(Scene):\n    def construct(self): self.wait(5)\n",
        ),
        input_dir=in_dir,
        output_dir=out_dir,
    )

    assert result.exit_code == 0
    assert (in_dir / "scene.py").read_text().startswith("from manim import *")
    assert (out_dir / "scene.mp4").read_bytes() == b"\x00MUXED"
    assert calls[0][0] == "manim"
    assert "GeneratedScene" in calls[0]
    assert calls[1][0] == "ffmpeg"
    assert "/in/audio.wav" in calls[1]
    assert calls[1][calls[1].index("-t") + 1] == "5.00"
    assert calls[1][-1] == "/out/scene.mp4"


async def test_manim_renderer_returns_failure_when_manim_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.render.manim import ManimRenderer

    async def fake_runner(*, image, command, input_dir, output_dir, limits, name):  # type: ignore[no-untyped-def]
        return RunResult(exit_code=1, stdout="", stderr="NameError: Squarea", timed_out=False)

    monkeypatch.setattr("app.render.manim.get_sandbox_runner", lambda: fake_runner)
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()
    (in_dir / "audio.wav").write_bytes(b"RIFF")

    result = await ManimRenderer().render(
        job_id=1,
        render_in=RenderInput(scene_index=0, text="n", duration=Decimal("5.00"), code="bad"),
        input_dir=in_dir,
        output_dir=out_dir,
    )
    assert result.exit_code != 0
    assert "Squarea" in result.stderr
