from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_session
from app.api.v1.runs import limiter
from app.core.config import settings
from app.db import models  # noqa: F401 - register models with metadata
from app.db.base import Base
from app.main import app
from app.services.seed import seed_all


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as db_session:
        yield db_session
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_session(session):
    await seed_all(session)
    return session


@pytest_asyncio.fixture
async def client(seeded_session, monkeypatch):
    monkeypatch.setattr(settings, "run_inline", False)
    limiter.reset()

    async def override():
        yield seeded_session

    app.dependency_overrides[get_session] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
