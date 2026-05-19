import asyncio
from typing import Any

from app.db.session import session_scope
from app.domain.enums import JobStatus, SceneStatus
from app.domain.state_machine import assert_transition
from app.logging import get_logger
from app.repositories.job_repo import JobRepo
from app.repositories.scene_repo import SceneRepo

log = get_logger("workers.orchestrator")

STUB_SCENE_COUNT = 3
_SCRIPTING_DELAY_S = 2.0
_PER_SCENE_DELAY_S = 1.0
_COMPOSING_DELAY_S = 1.0


async def run_video(ctx: dict[str, Any], job_id: int) -> None:
    no_sleep = bool(ctx.get("_test_no_sleep"))

    async def _sleep(seconds: float) -> None:
        if no_sleep:
            return
        await asyncio.sleep(seconds)

    async with session_scope() as session:
        job_repo = JobRepo(session)
        scene_repo = SceneRepo(session)

        current = await job_repo.get_status(job_id)
        if current is None:
            log.warning("orchestrator.skip_missing", job_id=job_id)
            return
        if current == JobStatus.CANCELLED:
            log.info("orchestrator.skip_cancelled", job_id=job_id)
            return
        if current == JobStatus.DONE:
            log.info("orchestrator.skip_done", job_id=job_id)
            return

        await _transition(job_repo, job_id, current, JobStatus.SCRIPTING)
        await _sleep(_SCRIPTING_DELAY_S)

        if await _is_cancelled(job_repo, job_id):
            return

        await scene_repo.bulk_insert_stubs(job_id=job_id, n=STUB_SCENE_COUNT)
        await _transition(job_repo, job_id, JobStatus.SCRIPTING, JobStatus.SCRIPT_READY)
        await _transition(job_repo, job_id, JobStatus.SCRIPT_READY, JobStatus.RENDERING)

        scenes = await scene_repo.list_by_job(job_id)
        for scene in scenes:
            if await _is_cancelled(job_repo, job_id):
                return
            await scene_repo.update_status(scene.id, SceneStatus.RENDERING)
            await _sleep(_PER_SCENE_DELAY_S)
            await scene_repo.update_status(scene.id, SceneStatus.DONE)
            await job_repo.set_progress(
                job_id,
                {"current_scene": scene.index + 1, "total": len(scenes), "stage": "stub_render"},
            )

        await _transition(job_repo, job_id, JobStatus.RENDERING, JobStatus.COMPOSING)
        await _sleep(_COMPOSING_DELAY_S)
        await _transition(job_repo, job_id, JobStatus.COMPOSING, JobStatus.DONE)
        log.info("orchestrator.completed", job_id=job_id)


async def _transition(repo: JobRepo, job_id: int, src: JobStatus, dst: JobStatus) -> None:
    assert_transition(src, dst)
    await repo.update_status(job_id, dst)
    log.info("job.transition", job_id=job_id, **{"from": src.value, "to": dst.value})


async def _is_cancelled(repo: JobRepo, job_id: int) -> bool:
    current = await repo.get_status(job_id)
    if current == JobStatus.CANCELLED:
        log.info("orchestrator.cancelled_mid_flight", job_id=job_id)
        return True
    return False
