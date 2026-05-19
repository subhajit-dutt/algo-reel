from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest_asyncio.fixture
async def client(_migrations: None) -> AsyncIterator[AsyncClient]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealth:
    async def test_healthz_ok(self, client: AsyncClient) -> None:
        r = await client.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    async def test_readyz_ok_when_pg_and_redis_up(self, client: AsyncClient) -> None:
        r = await client.get("/readyz")
        assert r.status_code == 200
        body = r.json()
        assert body["postgres"] is True
        assert body["redis"] is True
