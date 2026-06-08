from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scene
from app.domain.enums import SceneStatus
from app.domain.script import VideoScript


class SceneRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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

    async def set_duration(self, scene_id: int, seconds: Decimal) -> None:
        await self._session.execute(
            update(Scene)
            .where(Scene.id == scene_id)
            .values(duration_seconds=seconds.quantize(Decimal("0.01")))
        )

    async def get(self, scene_id: int) -> Scene | None:
        result = await self._session.execute(select(Scene).where(Scene.id == scene_id))
        return result.scalar_one_or_none()

    async def set_output_url(self, scene_id: int, url: str) -> None:
        await self._session.execute(
            update(Scene).where(Scene.id == scene_id).values(output_url=url)
        )
