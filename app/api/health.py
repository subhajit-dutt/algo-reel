from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.config import Settings, get_settings
from app.db.session import get_engine

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(settings: Settings = Depends(get_settings)) -> dict[str, bool]:
    pg_ok = await _ping_postgres()
    redis_ok = await _ping_redis(settings)
    body: dict[str, bool] = {"postgres": pg_ok, "redis": redis_ok}
    if not (pg_ok and redis_ok):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=body)
    return body


async def _ping_postgres() -> bool:
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _ping_redis(settings: Settings) -> bool:
    try:
        pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        await pool.ping()
        await pool.close()
        return True
    except Exception:
        return False
