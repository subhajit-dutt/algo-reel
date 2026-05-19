from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.db.session import get_engine
from app.deps import get_arq

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(arq: ArqRedis = Depends(get_arq)) -> dict[str, bool]:
    pg_ok = await _ping_postgres()
    redis_ok = await _ping_redis(arq)
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


async def _ping_redis(arq: ArqRedis) -> bool:
    try:
        await arq.ping()
        return True
    except Exception:
        return False
