from decimal import Decimal
from pathlib import Path

import pytest

from app.render.base import RenderInput
from app.render.sandbox import RunResult
from app.render.trivial import TrivialRenderer


async def test_builds_card_command_and_stages_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    async def fake_runner(
        *,
        image: str,
        command: list[str],
        input_dir: Path,
        output_dir: Path,
        limits: object,
        name: str,
    ) -> RunResult:
        captured["command"] = command
        captured["name"] = name
        captured["image"] = image
        (output_dir / "scene.mp4").write_bytes(b"\x00MP4")
        return RunResult(exit_code=0, stdout="", stderr="", timed_out=False)

    monkeypatch.setattr("app.render.trivial.get_sandbox_runner", lambda: fake_runner)

    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()
    (in_dir / "audio.wav").write_bytes(b"RIFF")

    renderer = TrivialRenderer()
    result = await renderer.render(
        job_id=7,
        render_in=RenderInput(scene_index=2, text="hello world", duration=Decimal("5.00")),
        input_dir=in_dir,
        output_dir=out_dir,
    )

    assert result.exit_code == 0
    assert (in_dir / "text.txt").read_text() == "hello world"
    command = captured["command"]
    assert isinstance(command, list)
    assert command[0] == "ffmpeg"
    assert "/in/audio.wav" in command
    assert command[command.index("-t") + 1] == "5.00"
    assert command[-1] == "/out/scene.mp4"
    assert "drawtext=fontfile=/opt/font.ttf:textfile=/in/text.txt" in " ".join(command)
    assert captured["name"] == "algoreel-render-7-2"
    assert captured["image"] == "algoreel-render:m4"
