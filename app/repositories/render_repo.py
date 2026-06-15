from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Render, Scene


class RenderRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start_attempt(self, scene_id: int, *, attempt: int) -> Render:
        render = Render(scene_id=scene_id, attempt=attempt, status="started")
        self._session.add(render)
        await self._session.flush()
        return render

    async def mark_succeeded(
        self, render_id: int, *, duration_ms: int, cost_usd: Decimal = Decimal("0")
    ) -> None:
        await self._session.execute(
            update(Render)
            .where(Render.id == render_id)
            .values(status="succeeded", duration_ms=duration_ms, cost_usd=cost_usd)
        )

    async def mark_failed(
        self,
        render_id: int,
        *,
        stderr: str,
        duration_ms: int | None = None,
        cost_usd: Decimal = Decimal("0"),
    ) -> None:
        await self._session.execute(
            update(Render)
            .where(Render.id == render_id)
            .values(status="failed", stderr=stderr, duration_ms=duration_ms, cost_usd=cost_usd)
        )

    async def total_cost_for_job(self, job_id: int) -> Decimal:
        result = await self._session.execute(
            select(func.coalesce(func.sum(Render.cost_usd), 0))
            .join(Scene, Scene.id == Render.scene_id)
            .where(Scene.job_id == job_id)
        )
        return Decimal(result.scalar_one())
