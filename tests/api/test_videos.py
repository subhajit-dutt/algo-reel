from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.workers.queues import ORCHESTRATOR_POOL_HEALTH_KEY


@pytest_asyncio.fixture
async def client(clean_db) -> AsyncIterator[AsyncClient]:
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest_asyncio.fixture(autouse=True)
async def orchestrator_alive(redis_client) -> AsyncIterator[None]:  # type: ignore[no-untyped-def]
    """Simulate a live orchestrator worker: arq maintains this key (TTL 61s) while
    running, and POST /api/videos rejects with 503 when it is absent."""
    await redis_client.set(ORCHESTRATOR_POOL_HEALTH_KEY, "ok", ex=61)
    yield
    await redis_client.delete(ORCHESTRATOR_POOL_HEALTH_KEY)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-secret-123"}


class TestCreateVideo:
    async def test_unauthorized_without_token(self, client: AsyncClient) -> None:
        r = await client.post("/api/videos", json={})
        assert r.status_code == 401

    async def test_unauthorized_with_wrong_token(self, client: AsyncClient) -> None:
        r = await client.post(
            "/api/videos",
            json={"prompt": "x", "renderer": "manim", "duration_target": 60, "voice": "alloy"},
            headers={"Authorization": "Bearer nope"},
        )
        assert r.status_code == 401

    async def test_422_on_invalid_duration(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        r = await client.post(
            "/api/videos",
            json={"prompt": "x", "renderer": "manim", "duration_target": 45, "voice": "alloy"},
            headers=auth_headers,
        )
        assert r.status_code == 422

    async def test_422_on_empty_prompt(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        r = await client.post(
            "/api/videos",
            json={"prompt": "", "renderer": "manim", "duration_target": 60, "voice": "alloy"},
            headers=auth_headers,
        )
        assert r.status_code == 422

    async def test_202_creates_and_returns_job(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        r = await client.post(
            "/api/videos",
            json={
                "prompt": "explain merge sort",
                "renderer": "manim",
                "duration_target": 60,
                "voice": "alloy",
            },
            headers=auth_headers,
        )
        assert r.status_code == 202
        body = r.json()
        assert body["id"] >= 1
        assert body["status"] == "queued"
        assert body["renderer"] == "manim"
        assert body["scenes"] == []

    async def test_503_when_orchestrator_pool_down(
        self, client: AsyncClient, auth_headers: dict[str, str], redis_client
    ) -> None:
        await redis_client.delete(ORCHESTRATOR_POOL_HEALTH_KEY)

        r = await client.post(
            "/api/videos",
            json={
                "prompt": "explain merge sort",
                "renderer": "manim",
                "duration_target": 60,
                "voice": "alloy",
            },
            headers=auth_headers,
        )

        assert r.status_code == 503
        assert "orchestrator worker" in r.json()["detail"]
        assert r.headers["retry-after"] == "60"


class TestGetVideo:
    async def test_404_when_missing(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        r = await client.get("/api/videos/9999", headers=auth_headers)
        assert r.status_code == 404

    async def test_returns_job(self, client: AsyncClient, auth_headers: dict[str, str]) -> None:
        created = (
            await client.post(
                "/api/videos",
                json={
                    "prompt": "x",
                    "renderer": "manim",
                    "duration_target": 30,
                    "voice": "alloy",
                },
                headers=auth_headers,
            )
        ).json()

        r = await client.get(f"/api/videos/{created['id']}", headers=auth_headers)

        assert r.status_code == 200
        assert r.json()["id"] == created["id"]


class TestDeleteVideo:
    async def test_404_when_missing(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        r = await client.delete("/api/videos/9999", headers=auth_headers)
        assert r.status_code == 404

    async def test_cancels_in_flight(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        created = (
            await client.post(
                "/api/videos",
                json={
                    "prompt": "x",
                    "renderer": "manim",
                    "duration_target": 60,
                    "voice": "alloy",
                },
                headers=auth_headers,
            )
        ).json()

        r = await client.delete(f"/api/videos/{created['id']}", headers=auth_headers)

        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    async def test_409_when_already_terminal(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        created = (
            await client.post(
                "/api/videos",
                json={
                    "prompt": "x",
                    "renderer": "manim",
                    "duration_target": 60,
                    "voice": "alloy",
                },
                headers=auth_headers,
            )
        ).json()
        await client.delete(f"/api/videos/{created['id']}", headers=auth_headers)
        r = await client.delete(f"/api/videos/{created['id']}", headers=auth_headers)

        assert r.status_code == 409


class TestResumeVideo:
    async def test_404_when_missing(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        r = await client.post("/api/videos/999999/resume", headers=auth_headers)
        assert r.status_code == 404

    async def test_409_when_not_partially_failed(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        # Create a job (lands in `queued`); resume requires `partially_failed` → 409
        created = (
            await client.post(
                "/api/videos",
                json={
                    "prompt": "x",
                    "renderer": "manim",
                    "duration_target": 60,
                    "voice": "alloy",
                },
                headers=auth_headers,
            )
        ).json()

        r = await client.post(f"/api/videos/{created['id']}/resume", headers=auth_headers)

        assert r.status_code == 409
