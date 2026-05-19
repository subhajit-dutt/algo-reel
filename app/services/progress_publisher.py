from typing import Any

from app.schemas.event import ProgressEvent


class ProgressPublisher:
    def __init__(self, redis: Any) -> None:
        self._redis = redis

    @staticmethod
    def channel(job_id: int) -> str:
        return f"job_progress:{job_id}"

    async def publish(self, event: ProgressEvent) -> None:
        await self._redis.publish(self.channel(event.job_id), event.model_dump_json())
