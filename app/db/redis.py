"""Shared Redis client factory.

Centralises construction so the API tier (lifespan-managed singleton on
`app.state.redis`) and the worker (short-lived per-job client) agree on
connection kwargs.
"""

from __future__ import annotations

import redis.asyncio as redis_async

from app.config import get_settings


def create_redis_client() -> redis_async.Redis:
    client: redis_async.Redis = redis_async.from_url(  # type: ignore[no-untyped-call]
        get_settings().redis_url, decode_responses=True
    )
    return client
