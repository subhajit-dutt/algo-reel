import asyncio
from typing import Any

from app.db.session import session_scope
from app.domain.enums import JobStatus, SceneStatus
from app.domain.state_machine import TERMINAL_JOB_STATUSES, assert_transition
from app.logging import get_logger
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo

log = get_logger("workers.orchestrator")

STUB_SCENE_COUNT = 3
_SCRIPTING_DELAY_S = 2.0
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

    try:
        async with session_scope() as session:
            await _execute(session, job_id, _sleep)
    except _AbortedError:
        log.info("orchestrator.aborted", job_id=job_id)


async def _execute(session: Any, job_id: int, sleep: Any) -> None:
    job_repo = JobRepo(session)
    scene_repo = SceneRepo(session)

    current = await job_repo.get_status(job_id)
    if current is None:
        log.warning("orchestrator.skip_missing", job_id=job_id)
        return
    if current in TERMINAL_JOB_STATUSES:
        log.info("orchestrator.skip_terminal", job_id=job_id, status=current.value)
        return

    if current == JobStatus.QUEUED:
        await _transition(job_repo, job_id, JobStatus.QUEUED, JobStatus.SCRIPTING)
        current = JobStatus.SCRIPTING

    if current == JobStatus.SCRIPTING:
        await sleep(_SCRIPTING_DELAY_S)
        if not await scene_repo.list_by_job(job_id):
            await scene_repo.bulk_insert_stubs(job_id=job_id, n=STUB_SCENE_COUNT)
        await _transition(job_repo, job_id, JobStatus.SCRIPTING, JobStatus.SCRIPT_READY)
        current = JobStatus.SCRIPT_READY

    if current == JobStatus.SCRIPT_READY:
        await _transition(job_repo, job_id, JobStatus.SCRIPT_READY, JobStatus.RENDERING)
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
            await job_repo.set_progress(
                job_id,
                {
                    "current_scene": scene.index + 1,
                    "total": len(scenes),
                    "stage": "stub_render",
                },
            )
        await _transition(job_repo, job_id, JobStatus.RENDERING, JobStatus.COMPOSING)
        current = JobStatus.COMPOSING

    if current == JobStatus.COMPOSING:
        await sleep(_COMPOSING_DELAY_S)
        await _transition(job_repo, job_id, JobStatus.COMPOSING, JobStatus.DONE)

    log.info("orchestrator.completed", job_id=job_id)


async def _transition(repo: JobRepo, job_id: int, src: JobStatus, dst: JobStatus) -> None:
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


async def _assert_not_terminal(repo: JobRepo, job_id: int) -> None:
    current = await repo.get_status(job_id)
    if current is None or current in TERMINAL_JOB_STATUSES:
        log.info(
            "orchestrator.checkpoint_terminal",
            job_id=job_id,
            status=current.value if current else None,
        )
        raise _AbortedError
