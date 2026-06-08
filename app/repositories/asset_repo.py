from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Asset
from app.domain.enums import AssetKind


class AssetRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        job_id: int,
        scene_id: int | None,
        kind: AssetKind,
        storage_key: str,
        byte_size: int,
        content_type: str,
    ) -> Asset:
        asset = Asset(
            job_id=job_id,
            scene_id=scene_id,
            kind=kind.value,
            storage_key=storage_key,
            bytes=byte_size,
            content_type=content_type,
        )
        self._session.add(asset)
        await self._session.flush()
        return asset

    async def audio_scene_ids(self, job_id: int) -> set[int]:
        result = await self._session.execute(
            select(Asset.scene_id).where(
                Asset.job_id == job_id, Asset.kind == AssetKind.AUDIO.value
            )
        )
        return {sid for sid in result.scalars().all() if sid is not None}

    async def storage_key_for(self, scene_id: int, kind: AssetKind) -> str:
        result = await self._session.execute(
            select(Asset.storage_key).where(Asset.scene_id == scene_id, Asset.kind == kind.value)
        )
        return result.scalar_one()
