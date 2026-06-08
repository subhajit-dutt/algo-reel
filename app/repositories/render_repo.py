from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Render


class RenderRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start_attempt(self, scene_id: int, *, attempt: int) -> Render:
        render = Render(scene_id=scene_id, attempt=attempt, status="started")
        self._session.add(render)
        await self._session.flush()
        return render

    async def mark_succeeded(self, render_id: int, *, duration_ms: int) -> None:
        await self._session.execute(
            update(Render)
            .where(Render.id == render_id)
            .values(status="succeeded", duration_ms=duration_ms)
        )

    async def mark_failed(
        self, render_id: int, *, stderr: str, duration_ms: int | None = None
    ) -> None:
        await self._session.execute(
            update(Render)
            .where(Render.id == render_id)
            .values(status="failed", stderr=stderr, duration_ms=duration_ms)
        )
