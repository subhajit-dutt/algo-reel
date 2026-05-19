import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer(
        "postgres:16-alpine", username="algo", password="algo", dbname="algoreel"
    ) as pg:
        raw = pg.get_connection_url()
        async_url = raw.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
            "postgresql://", "postgresql+asyncpg://"
        )
        yield async_url


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    with RedisContainer("redis:7-alpine") as r:
        host = r.get_container_host_ip()
        port = r.get_exposed_port(6379)
        yield f"redis://{host}:{port}/0"


@pytest.fixture(scope="session", autouse=True)
def _env(postgres_url: str, redis_url: str) -> Iterator[None]:
    os.environ["APP_ENV"] = "ci"
    os.environ["APP_SHARED_SECRET"] = "test-secret-123"
    os.environ["DATABASE_URL"] = postgres_url
    os.environ["REDIS_URL"] = redis_url
    os.environ["LOG_LEVEL"] = "INFO"
    from app.config import get_settings
    from app.db.session import get_engine, get_session_factory

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    yield


@pytest.fixture(scope="session", autouse=True)
def _migrations(_env: None) -> None:
    cfg = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture
async def db_session(_migrations: None) -> AsyncIterator[AsyncSession]:
    from app.config import get_settings

    engine = create_async_engine(get_settings().database_url, future=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def clean_db(db_session: AsyncSession) -> AsyncIterator[AsyncSession]:
    from sqlalchemy import text

    await db_session.execute(
        text("TRUNCATE jobs, scenes, renders, assets RESTART IDENTITY CASCADE")
    )
    await db_session.commit()
    yield db_session
