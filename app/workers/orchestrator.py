import asyncio
from typing import Any

from app.config import get_settings
from app.db.redis import create_redis_client
from app.db.session import session_scope
from app.domain.enums import JobStatus, Renderer, SceneStatus
from app.domain.state_machine import TERMINAL_JOB_STATUSES, assert_transition
from app.llm.budget import BudgetExceededError, enforce_budget
from app.llm.script_agent import generate_script
from app.logging import get_logger
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo
from app.schemas.event import ProgressEvent
from app.services.progress_publisher import ProgressPublisher

log = get_logger("workers.orchestrator")

_PER_SCENE_DELAY_S = 1.0
_COMPOSING_DELAY_S = 1.0


class _AbortedError(Exception):
    pass


async def run_video(ctx: dict[str, Any], job_id: int) -> None:
    no_sleep = bool(ctx.get("_test_no_sleep"))

    async def _sleep(seconds: float) -> None:
        if no_sleep:
            return
        await asyncio.sleep(seconds)

    redis = create_redis_client()
    publisher = ProgressPublisher(redis)
    try:
        async with session_scope() as session:
            await _execute(session, job_id, _sleep, publisher)
    except _AbortedError:
        log.info("orchestrator.aborted", job_id=job_id)
    finally:
        await redis.aclose()


async def _execute(
    session: Any,
    job_id: int,
    sleep: Any,
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
        await _transition(job_repo, publisher, job_id, JobStatus.SCRIPT_READY, JobStatus.RENDERING)
        current = JobStatus.RENDERING

    if current == JobStatus.RENDERING:
        scenes = await scene_repo.list_by_job(job_id)
        for scene in scenes:
            if scene.status == SceneStatus.DONE.value:
                continue
            await _assert_not_terminal(job_repo, job_id)
            await scene_repo.update_status(scene.id, SceneStatus.RENDERING)
            await sleep(_PER_SCENE_DELAY_S)
            await scene_repo.update_status(scene.id, SceneStatus.DONE)
            progress = {
                "current_scene": scene.index + 1,
                "total": len(scenes),
                "stage": "stub_render",
            }
            await job_repo.set_progress(job_id, progress)
            # Commit per-scene so a cancel mid-loop doesn't roll back finished work.
            await session.commit()
            await publisher.publish(
                ProgressEvent(
                    event="progress",
                    job_id=job_id,
                    status=JobStatus.RENDERING,
                    progress=progress,
                    scene_id=scene.id,
                )
            )
        await _transition(job_repo, publisher, job_id, JobStatus.RENDERING, JobStatus.COMPOSING)
        current = JobStatus.COMPOSING

    if current == JobStatus.COMPOSING:
        await sleep(_COMPOSING_DELAY_S)
        await _transition(job_repo, publisher, job_id, JobStatus.COMPOSING, JobStatus.DONE)

    log.info("orchestrator.completed", job_id=job_id)


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
