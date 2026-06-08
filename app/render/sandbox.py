import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SandboxLimits:
    memory: str
    cpus: str
    pids_limit: int
    timeout_seconds: int
    user: str


@dataclass(frozen=True)
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool


SandboxRunner = Callable[..., Awaitable[RunResult]]


def _build_argv(
    *,
    image: str,
    command: list[str],
    input_dir: Path,
    output_dir: Path,
    limits: SandboxLimits,
    name: str,
) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--user",
        limits.user,
        "--memory",
        limits.memory,
        "--cpus",
        limits.cpus,
        "--pids-limit",
        str(limits.pids_limit),
        "--tmpfs",
        "/tmp:rw,size=64m",
        "-v",
        f"{input_dir}:/in:ro",
        "-v",
        f"{output_dir}:/out",
        image,
        *command,
    ]


async def _kill(name: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        "docker",
        "kill",
        name,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()


async def run_sandboxed(
    *,
    image: str,
    command: list[str],
    input_dir: Path,
    output_dir: Path,
    limits: SandboxLimits,
    name: str,
) -> RunResult:
    argv = _build_argv(
        image=image,
        command=command,
        input_dir=input_dir,
        output_dir=output_dir,
        limits=limits,
        name=name,
    )
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), limits.timeout_seconds)
    except TimeoutError:
        await _kill(name)
        return RunResult(
            exit_code=124,
            stdout="",
            stderr=f"container '{name}' timed out after {limits.timeout_seconds}s",
            timed_out=True,
        )
    return RunResult(
        exit_code=proc.returncode if proc.returncode is not None else -1,
        stdout=stdout.decode(errors="replace"),
        stderr=stderr.decode(errors="replace"),
        timed_out=False,
    )


def get_sandbox_runner() -> SandboxRunner:
    return run_sandboxed
