from collections.abc import Callable
from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.config import get_settings
from app.logging import configure_logging
from app.workers.orchestrator import run_video

ORCHESTRATOR_QUEUE = "orchestrator_pool"


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def _on_startup(ctx: dict[str, Any]) -> None:
    configure_logging()


class WorkerSettings:
    functions: ClassVar[list[Callable[..., Any]]] = [run_video]
    queue_name: ClassVar[str] = ORCHESTRATOR_QUEUE
    max_tries: ClassVar[int] = 2
    job_timeout: ClassVar[int] = 1200
    keep_result: ClassVar[int] = 3600
    on_startup: ClassVar[Callable[..., Any]] = _on_startup
    redis_settings: ClassVar[RedisSettings] = redis_settings()
