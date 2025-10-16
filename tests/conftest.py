import asyncio
from typing import AsyncGenerator
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from main import app
from core.database import Base
from core.deps import get_db
from core.config import settings


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    url = make_url(settings.DATABASE_URL)
    TEST_DATABASE_URL = url.set(database="chromatin").render_as_string(
        hide_password=False
    )

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,  # Don't pool connections in tests
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.connect() as connection:
        async with connection.begin() as transaction:
            async with AsyncSession(
                bind=connection,
                expire_on_commit=False,
            ) as session:
                yield session

                await transaction.rollback()


@pytest.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = lambda: test_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(test_session: AsyncSession):
    from common.models import User
    from core.security import get_password_hash

    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpass123"),
        is_active=True,
        is_superuser=False,
    )

    test_session.add(user)
    await test_session.flush()
    await test_session.refresh(user)

    return user


@pytest.fixture
async def test_superuser(test_session: AsyncSession):
    """Create a test superuser"""
    from common.models import User
    from core.security import get_password_hash

    user = User(
        email="admin@example.com",
        username="admin",
        hashed_password=get_password_hash("adminpass123"),
        is_active=True,
        is_superuser=True,
    )

    test_session.add(user)
    await test_session.flush()
    await test_session.refresh(user)

    return user


@pytest.fixture
async def auth_headers(client: AsyncClient, test_user) -> dict[str, str]:
    """Get authentication headers for test user"""
    response = await client.post(
        "/api/auth/login",
        data={
            "username": test_user.email,  # OAuth2 uses 'username' field
            "password": "testpass123",
        },
    )

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def superuser_headers(client: AsyncClient, superuser) -> dict[str, str]:
    """Get authentication headers for superuser"""
    response = await client.post(
        "/api/auth/login",
        data={"username": superuser.email, "password": "adminpass123"},
    )

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def current_test_user(test_user):
    """Mock the get_current_user dependency to bypass authentication"""
    from core.security import get_current_user

    app.dependency_overrides[get_current_user] = lambda: test_user

    yield test_user

    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]


@pytest.fixture
def mock_superuser(test_superuser):
    """Mock current user as superuser"""
    from core.security import get_current_user

    app.dependency_overrides[get_current_user] = lambda: test_superuser

    yield test_superuser

    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
