import tempfile
import time
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.db.redis import create_redis_client
from app.db.session import session_scope
from app.domain.enums import AssetKind, JobStatus, SceneStatus
from app.logging import get_logger
from app.render.base import RenderError, RenderInput, get_renderer
from app.render.sandbox import SandboxLimits, get_sandbox_runner
from app.repositories.asset_repo import AssetRepo
from app.repositories.job_repo import JobRepo
from app.repositories.render_repo import RenderRepo
from app.repositories.scene_repo import SceneRepo
from app.schemas.event import ProgressEvent
from app.services.progress_publisher import ProgressPublisher
from app.storage import get_storage

log = get_logger("workers.render")


async def render_scene(ctx: dict[str, Any], scene_id: int, scene_total: int) -> None:
    storage = get_storage()
    renderer = get_renderer()
    redis = create_redis_client()
    publisher = ProgressPublisher(redis)
    try:
        async with session_scope() as session:
            scene_repo = SceneRepo(session)
            asset_repo = AssetRepo(session)
            render_repo = RenderRepo(session)
            job_repo = JobRepo(session)

            scene = await scene_repo.get(scene_id)
            if scene is None:
                log.warning("render.skip_missing", scene_id=scene_id)
                return
            if scene.status == SceneStatus.DONE.value:
                log.info("render.skip_done", scene_id=scene_id)
                return

            audio_key = await asset_repo.storage_key_for(scene_id, AssetKind.AUDIO)
            audio_bytes = await storage.get(audio_key)

            with (
                tempfile.TemporaryDirectory() as in_s,
                tempfile.TemporaryDirectory() as out_s,
            ):
                input_dir = Path(in_s)
                output_dir = Path(out_s)
                (input_dir / "audio.wav").write_bytes(audio_bytes)

                await scene_repo.update_status(scene_id, SceneStatus.RENDERING)
                render = await render_repo.start_attempt(scene_id, attempt=ctx.get("job_try", 1))
                progress = {
                    "current_scene": scene.index + 1,
                    "total": scene_total,
                    "stage": "render",
                }
                await job_repo.set_progress(scene.job_id, progress)
                await session.commit()
                await publisher.publish(
                    ProgressEvent(
                        event="progress",
                        job_id=scene.job_id,
                        status=JobStatus.RENDERING,
                        progress=progress,
                        scene_id=scene_id,
                    )
                )

                try:
                    started = time.monotonic()
                    result = await renderer.render(
                        job_id=scene.job_id,
                        render_in=RenderInput(
                            scene_index=scene.index,
                            text=scene.narration,
                            duration=scene.duration_seconds,
                        ),
                        input_dir=input_dir,
                        output_dir=output_dir,
                    )
                    duration_ms = int((time.monotonic() - started) * 1000)
                    mp4 = output_dir / "scene.mp4"
                    if (
                        result.exit_code != 0
                        or result.timed_out
                        or not mp4.exists()
                        or mp4.stat().st_size == 0
                    ):
                        raise RenderError(scene.index, result.stderr or "render produced no output")
                    data = mp4.read_bytes()
                    key = f"video/{scene.job_id}/{scene_id}.mp4"
                    stored = await storage.put(key, data, "video/mp4")
                    await asset_repo.record(
                        scene.job_id,
                        scene_id,
                        AssetKind.SCENE_MP4,
                        stored.key,
                        stored.bytes,
                        "video/mp4",
                    )
                    await scene_repo.set_output_url(scene_id, storage.url(key))
                    await scene_repo.update_status(scene_id, SceneStatus.DONE)
                    await render_repo.mark_succeeded(render.id, duration_ms=duration_ms)
                    await session.commit()
                except Exception as exc:
                    stderr = exc.stderr if isinstance(exc, RenderError) else str(exc)
                    await render_repo.mark_failed(render.id, stderr=stderr)
                    await scene_repo.update_status(scene_id, SceneStatus.FAILED)
                    await session.commit()
                    log.warning("render.failed", scene_id=scene_id, stderr=stderr[:500])
                    raise
    finally:
        await redis.aclose()


async def compose_video(ctx: dict[str, Any], job_id: int) -> None:
    s = get_settings()
    storage = get_storage()
    runner = get_sandbox_runner()
    redis = create_redis_client()
    publisher = ProgressPublisher(redis)
    try:
        async with session_scope() as session:
            job_repo = JobRepo(session)
            scene_repo = SceneRepo(session)
            asset_repo = AssetRepo(session)

            job = await job_repo.get(job_id)
            if job is None:
                log.warning("compose.skip_missing", job_id=job_id)
                return
            if job.output_url is not None:
                log.info("compose.skip_done", job_id=job_id)
                return

            progress = {"stage": "compose"}
            await job_repo.set_progress(job_id, progress)
            await session.commit()
            await publisher.publish(
                ProgressEvent(
                    event="progress",
                    job_id=job_id,
                    status=JobStatus.COMPOSING,
                    progress=progress,
                )
            )

            scenes = await scene_repo.list_by_job(job_id)
            with (
                tempfile.TemporaryDirectory() as in_s,
                tempfile.TemporaryDirectory() as out_s,
            ):
                input_dir = Path(in_s)
                output_dir = Path(out_s)
                lines: list[str] = []
                for sc in scenes:
                    key = await asset_repo.storage_key_for(sc.id, AssetKind.SCENE_MP4)
                    fname = f"{sc.index}.mp4"
                    (input_dir / fname).write_bytes(await storage.get(key))
                    lines.append(f"file '/in/{fname}'")
                (input_dir / "list.txt").write_text("\n".join(lines) + "\n")

                limits = SandboxLimits(
                    memory=s.render_memory,
                    cpus=s.render_cpus,
                    pids_limit=s.render_pids_limit,
                    timeout_seconds=s.render_timeout_seconds,
                    user=s.render_user,
                )
                command = [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    "/in/list.txt",
                    "-c",
                    "copy",
                    "/out/final.mp4",
                ]
                result = await runner(
                    image=s.render_image,
                    command=command,
                    input_dir=input_dir,
                    output_dir=output_dir,
                    limits=limits,
                    name=f"algoreel-compose-{job_id}",
                )
                mp4 = output_dir / "final.mp4"
                if (
                    result.exit_code != 0
                    or result.timed_out
                    or not mp4.exists()
                    or mp4.stat().st_size == 0
                ):
                    raise RuntimeError(result.stderr or "compose produced no output")

                key = f"video/{job_id}/final.mp4"
                stored = await storage.put(key, mp4.read_bytes(), "video/mp4")
                await asset_repo.record(
                    job_id, None, AssetKind.FINAL_MP4, stored.key, stored.bytes, "video/mp4"
                )
                await job_repo.set_output_url(job_id, storage.url(key))
                await session.commit()
    finally:
        await redis.aclose()
