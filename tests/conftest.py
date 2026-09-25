import asyncio
import uuid
from datetime import datetime
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from app import models  # noqa: F401
from app.models.tracked_vacancy import TrackedVacancy


_test_engine: AsyncEngine | None = None
_TestingSessionLocal: async_sessionmaker[AsyncSession] | None = None


def _get_test_engine() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Validate TEST_DATABASE_URL and build the test engine on first use.

    This runs lazily, only when a test actually needs the database (via
    the `client` fixture) — not at import time for the whole `tests/`
    directory. Pure-logic unit tests can then be collected and run
    without TEST_DATABASE_URL configured at all.
    """

    global _test_engine, _TestingSessionLocal

    if _test_engine is not None:
        return _test_engine, _TestingSessionLocal

    test_database_url = settings.test_database_url

    if not test_database_url:
        raise RuntimeError("TEST_DATABASE_URL is not configured")

    if test_database_url == settings.database_url:
        raise RuntimeError(
            "TEST_DATABASE_URL must differ from DATABASE_URL. "
            "Running tests against the main database would drop its tables."
        )

    test_database_name = make_url(test_database_url).database

    if not test_database_name or "test" not in test_database_name.split("_"):
        raise RuntimeError(
            "Tests must use a dedicated test database. "
            "TEST_DATABASE_URL's database name must contain 'test' as its "
            "own '_'-separated word (e.g. 'ai_career_test_db')."
        )

    _test_engine = create_async_engine(
        test_database_url,
        pool_pre_ping=True,
        poolclass=NullPool,
    )

    _TestingSessionLocal = async_sessionmaker(
        bind=_test_engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )

    return _test_engine, _TestingSessionLocal


async def recreate_test_database() -> None:
    test_engine, _ = _get_test_engine()

    async with test_engine.begin() as connection:
        await connection.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)


async def drop_test_database() -> None:
    test_engine, _ = _get_test_engine()

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    _, testing_session_local = _get_test_engine()

    async with testing_session_local() as session:
        yield session


def set_tracked_vacancy_fields(tracked_vacancy_id: int, **fields) -> None:
    """Write tracked vacancy fields straight to the test database.

    Sets up states the API deliberately does not allow to be set by hand
    (e.g. status=interview). Fields ending in `_at` accept ISO strings.
    """

    _, testing_session_local = _get_test_engine()

    values = {
        name: (
            datetime.fromisoformat(value)
            if name.endswith("_at") and isinstance(value, str)
            else value
        )
        for name, value in fields.items()
    }

    async def write_fields() -> None:
        async with testing_session_local() as session:
            await session.execute(
                update(TrackedVacancy)
                .where(TrackedVacancy.id == tracked_vacancy_id)
                .values(**values)
            )
            await session.commit()

    asyncio.run(write_fields())


@pytest.fixture()
def testing_session_factory():
    """Provide the async test session factory."""

    _, testing_session_local = _get_test_engine()
    return testing_session_local

@pytest.fixture()
def client():
    """Provide an isolated API client with a clean test database."""

    asyncio.run(recreate_test_database())
    fastapi_app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(fastapi_app) as test_client:
            yield test_client
    finally:
        fastapi_app.dependency_overrides.clear()
        asyncio.run(drop_test_database())


# Shared test helpers (not fixtures: called directly with arguments from
# inside test bodies, the same way each test file used to define them).

def create_test_user(client, prefix: str = "user") -> dict:
    """Create and return a registered test user.

    `prefix` labels the username/email so users created by different test
    files stay easy to tell apart in the database or logs, e.g.
    `create_test_user(client, prefix="vacancy")` -> "vacancy_user_<suffix>".
    """

    unique_suffix = uuid.uuid4().hex[:8]

    user_data = {
        "username": f"{prefix}_user_{unique_suffix}",
        "email": f"{prefix}_{unique_suffix}@example.com",
        "password": "TestPassword123!",
    }

    response = client.post(
        "/auth/register",
        json=user_data,
    )

    assert response.status_code == 201

    return user_data


def get_auth_headers(client, user_data: dict) -> dict[str, str]:
    """Log in a test user and return authorization headers."""

    response = client.post(
        "/auth/login",
        data={
            "username": user_data["username"],
            "password": user_data["password"],
        },
    )

    assert response.status_code == 200

    access_token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}",
    }