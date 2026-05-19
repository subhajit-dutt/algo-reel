import asyncio
from datetime import UTC, datetime

import pytest_asyncio

from app.domain.enums import JobStatus
from app.schemas.event import ProgressEvent
from app.services.progress_publisher import ProgressPublisher


@pytest_asyncio.fixture
async def publisher(redis_client):  # type: ignore[no-untyped-def]
    return ProgressPublisher(redis_client)


def _event(job_id: int) -> ProgressEvent:
    return ProgressEvent(
        event="transition",
        job_id=job_id,
        status=JobStatus.SCRIPTING,
        progress={},
        ts=datetime.now(tz=UTC),
    )


class TestProgressPublisher:
    async def test_publish_then_subscribe_round_trip(self, publisher, redis_client) -> None:  # type: ignore[no-untyped-def]
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(publisher.channel(123))
        try:
            await asyncio.sleep(0.05)  # let SUBSCRIBE land
            sent = _event(123)
            await publisher.publish(sent)
            msg = None
            for _ in range(50):
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                if msg:
                    break
            assert msg is not None
            received = ProgressEvent.model_validate_json(msg["data"])
            assert received == sent
        finally:
            await pubsub.unsubscribe()
            await pubsub.aclose()

    def test_channel_is_namespaced(self, publisher) -> None:  # type: ignore[no-untyped-def]
        assert publisher.channel(42) == "job_progress:42"
