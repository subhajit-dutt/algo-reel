import asyncio
from pathlib import Path

import pytest

from app.render.sandbox import RunResult, SandboxLimits, run_sandboxed

_LIMITS = SandboxLimits(
    memory="2g", cpus="1.0", pids_limit=256, timeout_seconds=120, user="10001:10001"
)


class _FakeProc:
    def __init__(self, *, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0,
                 hang: bool = False) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self._hang = hang

    async def communicate(self) -> tuple[bytes, bytes]:
        if self._hang:
            await asyncio.sleep(3600)
        return self._stdout, self._stderr

    async def wait(self) -> int:
        return self.returncode


async def test_builds_locked_down_argv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: dict[str, list[str]] = {}

    async def fake_exec(*argv: str, stdout: object = None, stderr: object = None) -> _FakeProc:
        seen["argv"] = list(argv)
        return _FakeProc(stdout=b"ok", stderr=b"", returncode=0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    result = await run_sandboxed(
        image="img:1", command=["ffmpeg", "-x"], input_dir=tmp_path / "in",
        output_dir=tmp_path / "out", limits=_LIMITS, name="c1",
    )
    assert result == RunResult(exit_code=0, stdout="ok", stderr="", timed_out=False)
    argv = seen["argv"]
    assert argv[:3] == ["docker", "run", "--rm"]
    for flag in ("--network=none", "--read-only", "--cap-drop=ALL",
                 "--security-opt=no-new-privileges"):
        assert flag in argv
    assert argv[argv.index("--name") + 1] == "c1"
    assert argv[argv.index("--user") + 1] == "10001:10001"
    assert argv[argv.index("--pids-limit") + 1] == "256"
    assert f"{tmp_path / 'in'}:/in:ro" in argv
    assert f"{tmp_path / 'out'}:/out" in argv
    assert argv[-3:] == ["img:1", "ffmpeg", "-x"]


async def test_timeout_kills_and_flags(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    async def fake_exec(*argv: str, stdout: object = None, stderr: object = None) -> _FakeProc:
        calls.append(list(argv))
        if list(argv)[:2] == ["docker", "kill"]:
            return _FakeProc(returncode=0)
        return _FakeProc(hang=True)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    limits = SandboxLimits(memory="2g", cpus="1.0", pids_limit=256, timeout_seconds=0, user="x")
    result = await run_sandboxed(
        image="img", command=["ffmpeg"], input_dir=tmp_path, output_dir=tmp_path,
        limits=limits, name="c2",
    )
    assert result.timed_out is True
    assert result.exit_code == 124
    assert any(c[:2] == ["docker", "kill"] for c in calls)
