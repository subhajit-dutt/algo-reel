import shutil
import tempfile
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.db.redis import create_redis_client
from app.db.session import session_scope
from app.domain.enums import AssetKind, JobStatus, Renderer, SceneStatus
from app.llm.budget import RenderBudgetExceededError, enforce_render_budget
from app.llm.manim_agent import generate_manim_code
from app.llm.manim_critic import critique
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
            job = await job_repo.get(scene.job_id)
            if job is None:
                log.warning("render.skip_missing_job", scene_id=scene_id)
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

                if Renderer(job.renderer) is Renderer.MANIM:
                    await _render_manim_scene(
                        session,
                        scene,
                        storage,
                        scene_repo,
                        asset_repo,
                        render_repo,
                        input_dir,
                        output_dir,
                    )
                else:
                    await _render_simple_scene(
                        session,
                        scene,
                        job,
                        storage,
                        scene_repo,
                        asset_repo,
                        render_repo,
                        input_dir,
                        output_dir,
                        ctx,
                    )
    finally:
        await redis.aclose()


async def _store_scene_mp4(
    storage: Any, asset_repo: AssetRepo, scene_repo: SceneRepo, scene: Any, mp4: Path
) -> None:
    data = mp4.read_bytes()
    key = f"video/{scene.job_id}/{scene.id}.mp4"
    stored = await storage.put(key, data, "video/mp4")
    await asset_repo.record(
        scene.job_id, scene.id, AssetKind.SCENE_MP4, stored.key, stored.bytes, "video/mp4"
    )
    await scene_repo.set_output_url(scene.id, storage.url(key))


async def _render_simple_scene(
    session: Any,
    scene: Any,
    job: Any,
    storage: Any,
    scene_repo: SceneRepo,
    asset_repo: AssetRepo,
    render_repo: RenderRepo,
    input_dir: Path,
    output_dir: Path,
    ctx: dict[str, Any],
) -> None:
    renderer = get_renderer(Renderer(job.renderer))
    render = await render_repo.start_attempt(scene.id, attempt=ctx.get("job_try", 1))
    try:
        started = time.monotonic()
        result = await renderer.render(
            job_id=scene.job_id,
            render_in=RenderInput(
                scene_index=scene.index, text=scene.narration, duration=scene.duration_seconds
            ),
            input_dir=input_dir,
            output_dir=output_dir,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        mp4 = output_dir / "scene.mp4"
        if result.exit_code != 0 or result.timed_out or not mp4.exists() or mp4.stat().st_size == 0:
            raise RenderError(scene.index, result.stderr or "render produced no output")
        await _store_scene_mp4(storage, asset_repo, scene_repo, scene, mp4)
        await scene_repo.update_status(scene.id, SceneStatus.DONE)
        await render_repo.mark_succeeded(render.id, duration_ms=duration_ms)
        await session.commit()
    except Exception as exc:
        stderr = exc.stderr if isinstance(exc, RenderError) else str(exc)
        await render_repo.mark_failed(render.id, stderr=stderr)
        await scene_repo.update_status(scene.id, SceneStatus.FAILED)
        await session.commit()
        log.warning("render.failed", scene_id=scene.id, stderr=stderr[:500])
        raise


def _clear_attempt_artifacts(output_dir: Path) -> None:
    media = output_dir / "m"
    if media.exists():
        shutil.rmtree(media)
    mp4 = output_dir / "scene.mp4"
    if mp4.exists():
        mp4.unlink()


async def _render_manim_scene(
    session: Any,
    scene: Any,
    storage: Any,
    scene_repo: SceneRepo,
    asset_repo: AssetRepo,
    render_repo: RenderRepo,
    input_dir: Path,
    output_dir: Path,
) -> None:
    s = get_settings()
    renderer = get_renderer(Renderer.MANIM)
    duration_str = str(scene.duration_seconds)
    prior_cost = await render_repo.total_cost_for_job(scene.job_id)
    loop_cost = Decimal("0")
    code: str | None = None
    last_stderr: str | None = None
    last_log = ""

    for attempt in range(1, s.manim_max_attempts + 1):
        model = s.llm_codegen_model if attempt == 1 else s.llm_codegen_retry_model
        try:
            enforce_render_budget(spent=prior_cost + loop_cost, cap=s.max_render_cost_usd)
        except RenderBudgetExceededError as exc:
            last_stderr = str(exc)
            break

        try:
            gen = await generate_manim_code(
                visual_prompt=scene.visual_prompt,
                narration=scene.narration,
                duration_seconds=duration_str,
                model=model,
                prev_code=code,
                stderr=last_stderr,
            )
            loop_cost += gen.cost_usd
            code = gen.code

            crit = await critique(code=code, duration_seconds=duration_str)
            loop_cost += crit.cost_usd
            if not crit.ok:
                last_stderr = "critic: " + "; ".join(crit.issues)
                continue

            _clear_attempt_artifacts(output_dir)
            render = await render_repo.start_attempt(scene.id, attempt=attempt)
            started = time.monotonic()
            result = await renderer.render(
                job_id=scene.job_id,
                render_in=RenderInput(
                    scene_index=scene.index,
                    text=scene.narration,
                    duration=scene.duration_seconds,
                    visual_prompt=scene.visual_prompt,
                    code=code,
                ),
                input_dir=input_dir,
                output_dir=output_dir,
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            last_log = (result.stdout + "\n" + result.stderr)[-8000:]
            mp4 = output_dir / "scene.mp4"
            if (
                result.exit_code == 0
                and not result.timed_out
                and mp4.exists()
                and mp4.stat().st_size > 0
            ):
                await _store_scene_mp4(storage, asset_repo, scene_repo, scene, mp4)
                await scene_repo.set_manim_code(scene.id, code)
                await scene_repo.update_status(scene.id, SceneStatus.DONE)
                await render_repo.mark_succeeded(
                    render.id, duration_ms=duration_ms, cost_usd=gen.cost_usd + crit.cost_usd
                )
                await job_add_cost(session, scene.job_id, loop_cost)
                await _store_manim_log(storage, asset_repo, scene, last_log)
                await session.commit()
                log.info("render.manim_done", scene_id=scene.id, attempt=attempt)
                return
            last_stderr = result.stderr or "render produced no output"
            await render_repo.mark_failed(
                render.id,
                stderr=last_stderr,
                duration_ms=duration_ms,
                cost_usd=gen.cost_usd + crit.cost_usd,
            )
            await session.commit()
            log.warning(
                "render.manim_attempt_failed", scene_id=scene.id, attempt=attempt, stderr=last_stderr[:500]
            )
        except Exception as exc:  # any codegen/render/storage error is a per-scene failure, never propagated
            await session.rollback()
            last_stderr = str(exc)
            log.warning("render.manim_attempt_error", scene_id=scene.id, attempt=attempt, error=str(exc)[:500])
            continue

    await job_add_cost(session, scene.job_id, loop_cost)
    await _store_manim_log(storage, asset_repo, scene, last_log)
    await _fail_manim_scene(session, scene_repo, scene, last_stderr or "manim attempts exhausted")


async def _fail_manim_scene(session: Any, scene_repo: SceneRepo, scene: Any, reason: str) -> None:
    await scene_repo.update_status(scene.id, SceneStatus.FAILED)
    await session.commit()
    log.warning("render.manim_failed", scene_id=scene.id, reason=reason[:500])


async def _store_manim_log(storage: Any, asset_repo: AssetRepo, scene: Any, text: str) -> None:
    key = f"logs/{scene.job_id}/{scene.id}.manim.log"
    stored = await storage.put(key, text.encode(), "text/plain")
    await asset_repo.record(
        scene.job_id, scene.id, AssetKind.MANIM_LOG, stored.key, stored.bytes, "text/plain"
    )


async def job_add_cost(session: Any, job_id: int, delta: Decimal) -> None:
    if delta > 0:
        await JobRepo(session).add_cost(job_id, delta)


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
