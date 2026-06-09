import asyncio
from decimal import Decimal
from typing import Any

from app.config import get_settings
from app.db.redis import create_redis_client
from app.db.session import session_scope
from app.domain.enums import AssetKind, JobStatus, Renderer, SceneStatus
from app.domain.state_machine import TERMINAL_JOB_STATUSES, assert_transition
from app.llm.budget import BudgetExceededError, enforce_budget
from app.llm.script_agent import generate_script
from app.logging import get_logger
from app.repositories.asset_repo import AssetRepo
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo
from app.schemas.event import ProgressEvent
from app.services.progress_publisher import ProgressPublisher
from app.storage import get_storage
from app.tts.client import get_tts_client
from app.tts.synthesizer import synthesize_scene
from app.workers.queues import RENDER_QUEUE

log = get_logger("workers.orchestrator")


class _AbortedError(Exception):
    pass


class _SceneTTSError(Exception):
    def __init__(self, scene_index: int, message: str) -> None:
        super().__init__(message)
        self.scene_index = scene_index
        self.message = message


class _SceneRenderError(Exception):
    def __init__(self, scene_index: int | None, message: str) -> None:
        super().__init__(message)
        self.scene_index = scene_index
        self.message = message


class _ComposeError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


async def run_video(ctx: dict[str, Any], job_id: int) -> None:
    redis = create_redis_client()
    publisher = ProgressPublisher(redis)
    try:
        async with session_scope() as session:
            await _execute(ctx, session, job_id, publisher)
    except _AbortedError:
        log.info("orchestrator.aborted", job_id=job_id)
    finally:
        await redis.aclose()


async def _execute(
    ctx: dict[str, Any],
    session: Any,
    job_id: int,
    publisher: ProgressPublisher,
) -> None:
    job_repo = JobRepo(session)
    scene_repo = SceneRepo(session)

    job = await job_repo.get(job_id)
    if job is None:
        log.warning("orchestrator.skip_missing", job_id=job_id)
        return
    current = JobStatus(job.status)
    if current in TERMINAL_JOB_STATUSES:
        log.info("orchestrator.skip_terminal", job_id=job_id, status=current.value)
        return

    if current == JobStatus.QUEUED:
        await _transition(job_repo, publisher, job_id, JobStatus.QUEUED, JobStatus.SCRIPTING)
        current = JobStatus.SCRIPTING

    if current == JobStatus.SCRIPTING:
        # Resume guard: a prior attempt already persisted the script + cost (the
        # intermediate commit at the bottom of this block succeeded but the
        # SCRIPT_READY transition didn't). Skip the LLM call so Arq's max_tries
        # retry doesn't bill the user a second time.
        if job.script is None:
            try:
                result = await generate_script(
                    prompt=job.user_prompt,
                    renderer=Renderer(job.renderer),
                    duration_target_seconds=job.duration_target_seconds,
                )
                s = get_settings()
                enforce_budget(
                    result.script,
                    cost_usd=result.cost_usd,
                    target_seconds=job.duration_target_seconds,
                    max_cost=s.max_script_cost_usd,
                    max_scenes=s.max_scenes_per_video,
                )
                await job_repo.set_script(job_id, result.script.model_dump(mode="json"))
                await job_repo.add_cost(job_id, result.cost_usd)
                await scene_repo.bulk_insert_from_script(job_id, result.script)
                # Commit script + cost + scenes before attempting the transition.
                # If the transition is rejected (user cancelled mid-LLM-call), the
                # LLM spend is still recorded — script generation cost real tokens
                # regardless of fate. Spec §13.
                await session.commit()
            except BudgetExceededError as e:
                await _fail(
                    job_repo,
                    publisher,
                    job_id,
                    JobStatus.SCRIPTING,
                    {"type": "budget_exceeded", "reason": e.reason, "value": str(e.value)},
                )
                return
            except Exception as e:
                await _fail(
                    job_repo,
                    publisher,
                    job_id,
                    JobStatus.SCRIPTING,
                    {"type": "llm_error", "message": str(e)},
                )
                return
        await _transition(job_repo, publisher, job_id, JobStatus.SCRIPTING, JobStatus.SCRIPT_READY)
        current = JobStatus.SCRIPT_READY

    if current == JobStatus.SCRIPT_READY:
        try:
            await _voice_all_scenes(session, job, job_repo, scene_repo, publisher)
        except _SceneTTSError as e:
            await _fail(
                job_repo,
                publisher,
                job_id,
                JobStatus.SCRIPT_READY,
                {"type": "tts_error", "scene_index": e.scene_index, "message": e.message},
            )
            return
        await _transition(job_repo, publisher, job_id, JobStatus.SCRIPT_READY, JobStatus.RENDERING)
        current = JobStatus.RENDERING

    if current == JobStatus.RENDERING:
        try:
            await _render_all_scenes(ctx, session, job_id, job_repo, scene_repo)
        except _SceneRenderError as e:
            await _fail(
                job_repo,
                publisher,
                job_id,
                JobStatus.RENDERING,
                {"type": "render_error", "scene_index": e.scene_index, "message": e.message},
            )
            return
        await _transition(job_repo, publisher, job_id, JobStatus.RENDERING, JobStatus.COMPOSING)
        current = JobStatus.COMPOSING

    if current == JobStatus.COMPOSING:
        # Commit the COMPOSING transition before awaiting compose: the compose
        # worker updates the jobs row on its own session, so the orchestrator must
        # release the row lock first (same reason as the RENDERING fan-out above).
        await session.commit()
        try:
            await _compose(ctx, job_id)
        except _ComposeError as e:
            await _fail(
                job_repo,
                publisher,
                job_id,
                JobStatus.COMPOSING,
                {"type": "compose_error", "message": e.message},
            )
            return
        await _transition(job_repo, publisher, job_id, JobStatus.COMPOSING, JobStatus.DONE)

    log.info("orchestrator.completed", job_id=job_id)


async def _voice_all_scenes(
    session: Any,
    job: Any,
    job_repo: JobRepo,
    scene_repo: SceneRepo,
    publisher: ProgressPublisher,
) -> None:
    s = get_settings()
    asset_repo = AssetRepo(session)
    storage = get_storage()
    tts_client = get_tts_client()

    # Cancellation is checked once here; a cancel during the gather lets in-flight
    # synthesis finish and the batch commit, then the SCRIPT_READY→RENDERING
    # transition aborts via the conditional UPDATE (spend recorded regardless of
    # fate — same property as the SCRIPTING block).
    await _assert_not_terminal(job_repo, job.id)

    scenes = await scene_repo.list_by_job(job.id)
    # A scene's audio asset row and its set_duration land in the SAME commit below,
    # so any scene already in `already_voiced` necessarily already has its measured
    # duration — that's why skipped scenes are not re-voiced or re-dured here.
    already_voiced = await asset_repo.audio_scene_ids(job.id)
    pending = [scene for scene in scenes if scene.id not in already_voiced]

    voice = job.voice or s.tts_voice_default
    sem = asyncio.Semaphore(s.tts_max_concurrency)

    async def _synth_one(scene: Any) -> tuple[Any, Any, Any]:
        try:
            async with sem:
                result = await synthesize_scene(
                    narration=scene.narration, voice=voice, client=tts_client
                )
                stored = await storage.put(
                    f"audio/{job.id}/{scene.id}.wav", result.audio_bytes, result.content_type
                )
        # Any synth OR storage failure for a scene becomes a typed tts_error that
        # fails the whole job (audio is a hard dependency for rendering).
        except Exception as exc:
            raise _SceneTTSError(scene.index, str(exc)) from exc
        return scene, result, stored

    # Concurrency is on the OpenAI calls + file writes only; gather returns plain
    # values. All DB writes below run sequentially on the single AsyncSession,
    # which is not safe for concurrent use across tasks.
    outcomes = await asyncio.gather(*[_synth_one(scene) for scene in pending])

    total_cost = Decimal("0")
    total = len(scenes)
    for scene, result, stored in outcomes:
        await asset_repo.record(
            job.id, scene.id, AssetKind.AUDIO, stored.key, stored.bytes, result.content_type
        )
        await scene_repo.set_duration(scene.id, result.duration_seconds)
        total_cost += result.cost_usd
        progress = {"current_scene": scene.index + 1, "total": total, "stage": "tts"}
        await job_repo.set_progress(job.id, progress)
        await publisher.publish(
            ProgressEvent(
                event="progress",
                job_id=job.id,
                status=JobStatus.SCRIPT_READY,
                progress=progress,
                scene_id=scene.id,
            )
        )
    if total_cost > 0:
        await job_repo.add_cost(job.id, total_cost)
    await session.commit()


async def _render_all_scenes(
    ctx: dict[str, Any],
    session: Any,
    job_id: int,
    job_repo: JobRepo,
    scene_repo: SceneRepo,
) -> None:
    await _assert_not_terminal(job_repo, job_id)
    # Commit the RENDERING transition before fanning out: the render-pool workers
    # update the jobs row (set_progress) on their own sessions, so the orchestrator
    # must not hold an uncommitted row lock on it across the multi-minute gather.
    await session.commit()
    pool = ctx["redis"]
    s = get_settings()
    scenes = await scene_repo.list_by_job(job_id)
    scene_total = len(scenes)
    pending = [sc for sc in scenes if sc.status != SceneStatus.DONE.value]
    handles = []
    for sc in pending:
        handle = await pool.enqueue_job(
            "render_scene", sc.id, scene_total, _queue_name=RENDER_QUEUE
        )
        if handle is None:
            raise _SceneRenderError(sc.index, f"enqueue returned None for scene {sc.id}")
        handles.append(handle)
    try:
        await asyncio.gather(*[h.result(timeout=s.render_result_timeout_seconds) for h in handles])
    except Exception as exc:
        session.expire_all()
        refreshed = await scene_repo.list_by_job(job_id)
        failed = next((sc for sc in refreshed if sc.status == SceneStatus.FAILED.value), None)
        raise _SceneRenderError(failed.index if failed else None, str(exc)) from exc


async def _compose(ctx: dict[str, Any], job_id: int) -> None:
    pool = ctx["redis"]
    s = get_settings()
    handle = await pool.enqueue_job("compose_video", job_id, _queue_name=RENDER_QUEUE)
    if handle is None:
        raise _ComposeError(f"enqueue returned None for compose {job_id}")
    try:
        await handle.result(timeout=s.compose_result_timeout_seconds)
    except Exception as exc:
        raise _ComposeError(str(exc)) from exc


async def _transition(
    repo: JobRepo,
    publisher: ProgressPublisher,
    job_id: int,
    src: JobStatus,
    dst: JobStatus,
) -> None:
    assert_transition(src, dst)
    updated = await repo.update_status(job_id, dst, expected_from=src)
    if not updated:
        actual = await repo.get_status(job_id)
        actual_value = actual.value if actual is not None else None
        log.info(
            "job.transition_aborted",
            job_id=job_id,
            **{"from": src.value, "to": dst.value, "actual": actual_value},
        )
        raise _AbortedError
    log.info("job.transition", job_id=job_id, **{"from": src.value, "to": dst.value})
    event_kind = "done" if dst == JobStatus.DONE else "transition"
    await publisher.publish(
        ProgressEvent(
            event=event_kind,
            job_id=job_id,
            status=dst,
            progress={},
        )
    )


async def _fail(
    repo: JobRepo,
    publisher: ProgressPublisher,
    job_id: int,
    src: JobStatus,
    error: dict[str, Any],
) -> None:
    await repo.set_error(job_id, error)
    updated = await repo.update_status(job_id, JobStatus.FAILED, expected_from=src)
    if not updated:
        log.info("orchestrator.fail_aborted", job_id=job_id)
        return
    log.info("job.failed", job_id=job_id, error=error)
    await publisher.publish(
        ProgressEvent(
            event="failed",
            job_id=job_id,
            status=JobStatus.FAILED,
            progress={},
            error=error,
        )
    )


async def _assert_not_terminal(repo: JobRepo, job_id: int) -> None:
    current = await repo.get_status(job_id)
    if current is None or current in TERMINAL_JOB_STATUSES:
        log.info(
            "orchestrator.checkpoint_terminal",
            job_id=job_id,
            status=current.value if current else None,
        )
        raise _AbortedError
