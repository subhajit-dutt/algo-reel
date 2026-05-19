from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scene
from app.domain.enums import SceneStatus
from app.domain.script import VideoScript


class SceneRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_insert_stubs(self, *, job_id: int, n: int) -> list[Scene]:
        scenes = [
            Scene(
                job_id=job_id,
                index=i,
                narration=f"[stub narration {i}]",
                visual_prompt=f"[stub visual {i}]",
                duration_seconds=Decimal("0.00"),
                status=SceneStatus.PENDING.value,
            )
            for i in range(n)
        ]
        self._session.add_all(scenes)
        await self._session.flush()
        return scenes

    async def bulk_insert_from_script(self, job_id: int, script: VideoScript) -> list[Scene]:
        scenes = [
            Scene(
                job_id=job_id,
                index=s.index,
                narration=s.narration,
                visual_prompt=s.visual_prompt,
                duration_seconds=Decimal(str(s.duration_seconds)).quantize(Decimal("0.01")),
                status=SceneStatus.PENDING.value,
            )
            for s in script.scenes
        ]
        self._session.add_all(scenes)
        await self._session.flush()
        return scenes

    async def list_by_job(self, job_id: int) -> list[Scene]:
        result = await self._session.execute(
            select(Scene).where(Scene.job_id == job_id).order_by(Scene.index)
        )
        return list(result.scalars().all())

    async def update_status(self, scene_id: int, status: SceneStatus) -> None:
        await self._session.execute(
            update(Scene).where(Scene.id == scene_id).values(status=status.value)
        )
