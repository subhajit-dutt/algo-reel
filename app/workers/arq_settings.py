from arq.connections import RedisSettings

from app.config import get_settings
from app.workers.orchestrator import run_video

ORCHESTRATOR_QUEUE = "orchestrator_pool"


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    functions = [run_video]
    queue_name = ORCHESTRATOR_QUEUE
    max_tries = 2
    job_timeout = 1200
    keep_result = 3600
    redis_settings = _redis_settings()
